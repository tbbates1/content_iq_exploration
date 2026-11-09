#!/usr/bin/env python3
"""Mirror the public ContentIQ docs to Markdown.

Source: https://contentiq.symplistic.ai/documentation/
The docs site is a React single-page app, so each page is rendered with
headless Chrome before it is converted. Release-note pages are discovered
from the Releases index, so new versions are picked up automatically.

Requirements: Google Chrome, plus `pip install beautifulsoup4 markdownify`.

Usage:
    python3 scripts/mirror_contentiq_docs.py            # writes docs/contentiq/
    python3 scripts/mirror_contentiq_docs.py OUT_DIR

Set CHROME=/path/to/chrome if Chrome is not in the default macOS location.
The hand-written docs/contentiq/README.md is never overwritten.
"""
import concurrent.futures as cf
import datetime as dt
import os
import posixpath
import re
import subprocess
import sys
import tempfile

from bs4 import BeautifulSoup
from markdownify import MarkdownConverter

SITE = "https://contentiq.symplistic.ai"
CHROME = os.environ.get(
    "CHROME", "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
)
FIXED_PAGES = [
    "/documentation",
    "/documentation/latest",
    "/documentation/guide",
    "/documentation/api",
    "/documentation/mcp",
    "/documentation/releases",
]
MOCK_MODAL = (
    "## Active Ingestions\n\nWebsite IngestSupport AgentManualView Status"
    "OneDrive IngestHR Policy AgentAuto-scheduledView StatusClose"
)
MOCK_MODAL_MD = (
    '*Illustration from the docs, "Active Ingestions" modal:*\n\n'
    "| Connector | Target agent | Trigger | |\n| --- | --- | --- | --- |\n"
    "| Website Ingest | Support Agent | Manual | View Status |\n"
    "| OneDrive Ingest | HR Policy Agent | Auto-scheduled | View Status |"
)


def local_file(doc_path):
    """Map a /documentation/... path to a Markdown file inside the mirror."""
    p = doc_path.rstrip("/")
    if p == "/documentation":
        return "home.md"
    if p == "/documentation/releases":
        return "releases/README.md"
    m = re.fullmatch(r"/documentation/releases/(v[\w.]+)", p)
    if m:
        return f"releases/{m.group(1)}.md"
    m = re.fullmatch(r"/documentation/(\w+)", p)
    return f"{m.group(1)}.md" if m else None


def render(doc_path):
    """Return the DOM of a docs page after the SPA has rendered it."""
    with tempfile.TemporaryDirectory() as profile:
        out = subprocess.run(
            [
                CHROME,
                "--headless=new",
                "--disable-gpu",
                "--no-first-run",
                f"--user-data-dir={profile}",
                "--virtual-time-budget=15000",
                "--dump-dom",
                SITE + doc_path,
            ],
            capture_output=True,
            text=True,
            timeout=120,
        )
    if "docs-page-header" not in out.stdout and "<main" not in out.stdout:
        raise RuntimeError(f"{doc_path}: page did not render")
    return out.stdout


class Converter(MarkdownConverter):
    def convert_pre(self, el, text, parent_tags=None, **kwargs):
        code = el.get_text()
        code_el = el.find("code")
        classes = " ".join((code_el.get("class") if code_el else None) or el.get("class") or [])
        m = re.search(r"language-(\w+)", classes)
        lang = m.group(1) if m else ""
        if not lang:
            s = code.lstrip()
            lang = "bash" if s.startswith("curl") else "json" if s[:1] in "{[" else ""
        return f"\n\n```{lang}\n{code.rstrip()}\n```\n\n"


def to_markdown(html, doc_path, today):
    soup = BeautifulSoup(html, "html.parser")
    art = soup.find("article", class_="docs-article") or soup.find("main")
    for t in art.find_all(["button", "svg", "script", "style", "noscript"]):
        t.decompose()
    for t in art.select('[aria-hidden="true"]'):
        t.decompose()

    here = posixpath.dirname(local_file(doc_path))
    for a in art.find_all("a", href=True):
        # Card links hold a title and a blurb in separate spans; keep them apart.
        parts = list(a.stripped_strings)
        if len(parts) >= 2 and a.find(["span", "div", "p"]):
            joined = []
            for x in parts:
                if x in ("Latest", "New") and joined:
                    joined[-1] += f" ({x})"
                else:
                    joined.append(x)
            a.clear()
            a.string = " — ".join(joined)
        # Point links between docs pages at the local mirror.
        href = a["href"]
        path, _, frag = href.partition("#")
        target = local_file(path) if path.startswith("/documentation") else None
        if target:
            rel = posixpath.relpath(target, here or ".")
            a["href"] = rel + (f"#{frag}" if frag else "")
        elif href.startswith("/"):
            a["href"] = SITE + href

    md = Converter(
        heading_style="ATX", bullets="-", escape_asterisks=False, escape_underscores=False
    ).convert_soup(art)
    md = md.replace(MOCK_MODAL, MOCK_MODAL_MD)
    md = re.sub(r"\n{3,}", "\n\n", md).strip() + "\n"
    header = (
        f"<!-- Source: {SITE}{doc_path} (rendered {today}). "
        "Mirror for reference; the live page is the source of truth. -->\n\n"
    )
    return header + md


def main():
    out_dir = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "docs", "contentiq"
    )
    today = dt.date.today().isoformat()

    releases_html = render("/documentation/releases")
    versions = sorted(set(re.findall(r'href="(/documentation/releases/v[\w.]+)"', releases_html)))
    pages = FIXED_PAGES + versions

    with cf.ThreadPoolExecutor(max_workers=5) as pool:
        rendered = dict(zip(pages, pool.map(render, pages)))

    for doc_path in pages:
        dst = os.path.join(out_dir, local_file(doc_path))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        with open(dst, "w", encoding="utf-8") as f:
            f.write(to_markdown(rendered[doc_path], doc_path, today))
        print(f"{local_file(doc_path):28} <- {SITE}{doc_path}")
    print(f"{len(pages)} pages written to {os.path.normpath(out_dir)}")


if __name__ == "__main__":
    main()

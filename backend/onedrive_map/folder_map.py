"""Queries over the OneDrive folder map (folder_map.json, built by backend/build_map.py).

ContentIQ stores each file by its file name only, so these functions translate between
folder paths (what users mean) and file names (what ContentIQ search returns).
"""
from __future__ import annotations

import difflib
import json
import re
from functools import lru_cache
from pathlib import Path

MAP_FILE = Path(__file__).with_name("folder_map.json")

STOPWORDS = {
    "a", "an", "and", "the", "of", "for", "in", "on", "at", "to", "with", "our", "we",
    "project", "projects", "client", "rfq", "rfqs", "current", "latest", "old", "older",
    "previous", "last", "ago", "years", "year", "installation", "job",
}


@lru_cache(maxsize=1)
def load_map() -> dict:
    data = json.loads(MAP_FILE.read_text(encoding="utf-8"))
    files = [f for p in data["projects"] for f in p["files"]]
    names: dict[str, list[str]] = {}
    for f in files:
        names.setdefault(f["name"].lower(), []).append(f["path"])
    data["_files"] = files
    data["_names"] = names
    data["_by_path"] = {p["path"].lower(): p for p in data["projects"]}
    return data


def _tokens(text: str) -> list[str]:
    return [t for t in re.split(r"[^a-z0-9]+", text.lower()) if t and t not in STOPWORDS]


def _hit(q: str, hay: list[str]) -> bool:
    for h in hay:
        if q == h:
            return True
        if len(q) >= 3 and len(h) >= 3 and (q in h or h in q):
            return True
        if len(q) >= 4 and difflib.SequenceMatcher(None, q, h).ratio() >= 0.8:
            return True
    return False


def _norm(path: str) -> str:
    data = load_map()
    path = path.strip().strip("/")
    if not path:
        return data["root"]
    if path.split("/")[0].lower() != data["root"].lower():
        path = f"{data['root']}/{path}"
    return path


def _project(path: str) -> dict | None:
    return load_map()["_by_path"].get(_norm(path).lower())


def _search_phrase(p: dict) -> str:
    return f"{p['client']} {p['year']} {p['title']}" if p["year"] else f"{p['client']} {p['title']}"


def _summary(p: dict) -> dict:
    return {
        "project_path": p["path"],
        "client": p["client"],
        "project": p["title"],
        "year": p["year"],
        "file_count": len(p["files"]),
    }


def find_projects(query: str = "", client: str = "", year_from: int | None = None,
                  year_to: int | None = None, limit: int = 10) -> dict:
    data = load_map()
    q = _tokens(query)
    c = _tokens(client)
    scored = []
    for p in data["projects"]:
        if year_from is not None and (p["year"] or 0) < year_from:
            continue
        if year_to is not None and (p["year"] or 9999) > year_to:
            continue
        if c and not all(_hit(t, _tokens(p["client"])) for t in c):
            continue
        hay = _tokens(f"{p['client']} {p['title']} {p['year']} {' '.join(p['codes'])}")
        hits = sum(_hit(t, hay) for t in q)
        if q and hits == 0:
            continue
        scored.append((hits, p))
    scored.sort(key=lambda x: (-x[0], -(x[1]["year"] or 0), x[1]["path"]))
    return {
        "query": query,
        "client": client,
        "year_from": year_from,
        "year_to": year_to,
        "total_matches": len(scored),
        "projects": [dict(_summary(p), matched_terms=f"{h}/{len(q)}") for h, p in scored[:limit]],
        "note": "Sorted by how many query words match, then newest first.",
    }


def list_folder(path: str = "") -> dict:
    data = load_map()
    base = _norm(path)
    prefix = base.lower() + "/"
    folders: dict[str, int] = {}
    files = []
    for f in data["_files"]:
        if not f["path"].lower().startswith(prefix):
            continue
        rest = f["path"][len(prefix):].split("/")
        if len(rest) == 1:
            files.append({"name": f["name"], "path": f["path"], "modified": f["modified"], "size": f["size"]})
        else:
            folders[rest[0]] = folders.get(rest[0], 0) + 1
    if not folders and not files:
        return {"path": base, "error": "Folder not found in the map. List its parent folder or use find_projects."}
    return {
        "path": base,
        "folders": [{"name": n, "path": f"{base}/{n}", "file_count": k} for n, k in sorted(folders.items())],
        "files": files,
    }


def list_project_files(project_path: str) -> dict:
    data = load_map()
    p = _project(project_path)
    if p is None:
        return {"project_path": project_path, "error": "Project folder not found. Use find_projects to get a project_path."}
    files = [{
        "name": f["name"],
        "path": f["path"],
        "modified": f["modified"],
        "size": f["size"],
        "name_shared_with_other_projects": len(data["_names"][f["name"].lower()]) > 1,
    } for f in p["files"]]
    keywords = [p["client"], p["title"]] + ([str(p["year"])] if p["year"] else []) + p["codes"]
    return dict(
        _summary(p),
        search_phrase=_search_phrase(p),
        search_keywords=keywords,
        files=files,
        note="ContentIQ identifies files by name only. Use match_sources to check which search results belong to this project.",
    )


def match_sources(project_path: str, source_names: list[str]) -> dict:
    data = load_map()
    p = _project(project_path)
    if p is None:
        return {"project_path": project_path, "error": "Project folder not found. Use find_projects to get a project_path."}
    own = {f["name"].lower() for f in p["files"]}
    details, keep, drop = [], [], []
    for s in source_names:
        name = s.strip().replace("\\", "/").split("/")[-1].lower()
        paths = data["_names"].get(name, [])
        if name in own:
            status = "in_project" if len(paths) == 1 else "in_project_but_name_shared"
            keep.append(s)
        else:
            status = "other_project" if paths else "not_in_map"
            drop.append(s)
        details.append({"source": s, "status": status, "paths": paths[:5]})
    return {
        "project_path": p["path"],
        "keep": keep,
        "drop": drop,
        "details": details,
        "note": "Use only passages from 'keep'. For 'in_project_but_name_shared', use the passage only if its text names this project.",
    }


def map_info() -> dict:
    data = load_map()
    return {
        "source": data["source"],
        "root": data["root"],
        "built_at": data["built_at"],
        "clients": len({p["client"] for p in data["projects"]}),
        "projects": len(data["projects"]),
        "files": len(data["_files"]),
    }

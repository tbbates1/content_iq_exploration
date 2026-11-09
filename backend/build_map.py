#!/usr/bin/env python3
"""Build the folder map that the onedrive_map MCP server answers from.

Today the source is a local folder: synthetic_data/Clients stands in for the client
OneDrive folder that ContentIQ ingests. In production the same records would come
from Microsoft Graph (driveItem delta on the Clients folder), and only this file changes.

Usage:
    python backend/build_map.py                     # synthetic_data/Clients -> onedrive_map/folder_map.json
    python backend/build_map.py --source PATH --root-name Clients
"""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DEFAULT_SOURCE = REPO / "synthetic_data" / "Clients"
DEFAULT_OUT = Path(__file__).resolve().parent / "onedrive_map" / "folder_map.json"

PROJECT_FOLDER = re.compile(r"^(?P<year>\d{4})_(?P<title>.+)$")


def iso_mtime(path: Path) -> str:
    return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat(timespec="seconds")


def build(source: Path, root_name: str) -> dict:
    """Walk <root>/<client>/<project>/... and return the map as plain JSON data."""
    projects = []
    for client_dir in sorted(p for p in source.iterdir() if p.is_dir()):
        client = client_dir.name.replace("_", " ")
        for project_dir in sorted(p for p in client_dir.iterdir() if p.is_dir()):
            m = PROJECT_FOLDER.match(project_dir.name)
            year = int(m["year"]) if m else None
            title = (m["title"] if m else project_dir.name).replace("_", " ")
            project_path = f"{root_name}/{client_dir.name}/{project_dir.name}"
            files = []
            for f in sorted(project_dir.rglob("*")):
                if not f.is_file() or f.name.startswith("."):
                    continue
                rel = f.relative_to(project_dir).as_posix()
                files.append({
                    "name": f.name,
                    "path": f"{project_path}/{rel}",
                    "modified": iso_mtime(f),
                    "size": f.stat().st_size,
                })
            codes = sorted({f["name"].split("-")[0] for f in files if "-" in f["name"]})
            projects.append({
                "path": project_path,
                "client": client,
                "client_folder": client_dir.name,
                "folder": project_dir.name,
                "title": title,
                "year": year,
                "codes": codes,
                "files": files,
            })
    return {
        "source": f"local:{source.relative_to(REPO) if source.is_relative_to(REPO) else source}",
        "root": root_name,
        "built_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "projects": projects,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--source", type=Path, default=DEFAULT_SOURCE, help="folder that stands in for the OneDrive Clients folder")
    ap.add_argument("--root-name", default="Clients", help="name of that folder in OneDrive")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    data = build(args.source.resolve(), args.root_name)
    args.out.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    n_files = sum(len(p["files"]) for p in data["projects"])
    names = [f["name"] for p in data["projects"] for f in p["files"]]
    print(f"{args.out.relative_to(REPO)}: {len({p['client'] for p in data['projects']})} clients, "
          f"{len(data['projects'])} projects, {n_files} files, {len(set(names))} unique file names")


if __name__ == "__main__":
    main()

# OneDrive folder-map backend

An MCP server that gives watsonx Orchestrate agents a map of the client OneDrive (`Clients/<client>/<year>_<project>/<files>`). ContentIQ stores files by name only, so the agents use this map to find a project's files and to keep only the ContentIQ search results that come from them.

The architecture is drawn in [`docs/architecture/project-searcher.html`](../docs/architecture/project-searcher.html).

## What runs where

| Part | Where | What it does |
|---|---|---|
| `build_map.py` | Your machine | Walks the drive and writes `onedrive_map/folder_map.json`. Today the drive is `synthetic_data/files_system_example`. Later it would read Microsoft Graph. |
| `onedrive_map/` | Hosted by watsonx Orchestrate (local MCP toolkit, stdio) | `server.py` serves the tools below from `folder_map.json`. Nothing has to run on your machine. |
| `wxo/project_searcher.yaml` | watsonx Orchestrate | Agent: resolves one project, searches ContentIQ (the client-drive agent's search tool), keeps only that project's results. |
| `wxo/rfq_assistant.yaml` | watsonx Orchestrate | Top agent: splits the question by project and calls Project Searcher for each part. |

## Tools

| Tool | Input | Output |
|---|---|---|
| `find_projects` | words, client, year range | matching project folders, best match first, then newest |
| `list_folder` | folder path | its subfolders and files |
| `list_project_files` | project_path | the project's files with dates, plus a `search_phrase` and `search_keywords` for ContentIQ queries |
| `match_sources` | project_path, ContentIQ source names | `keep` (this project) and `drop` (other projects or unknown), flags names shared across projects |
| `map_info` | none | where the map came from, when it was built, counts |

## Build, test, deploy

Setup (venv, `.env`, ContentIQ agent) is in the main [`README.md`](../README.md). `scripts/deploy_wxo.sh` runs all of the steps below. To run them one by one:

```bash
.venv/bin/python backend/build_map.py          # build onedrive_map/folder_map.json (not committed)
.venv/bin/python backend/smoke_test.py         # start the server over stdio and call every tool
.venv/bin/python backend/onedrive_map/server.py --http   # optional: serve it at http://127.0.0.1:8765/mcp

# Upload the server to Orchestrate (re-run after changing the map or the code).
# To replace an existing toolkit, remove it first: orchestrate toolkits remove -n onedrive_map
.venv/bin/orchestrate toolkits add --kind mcp --name onedrive_map \
  --description "Folder map of the client OneDrive" \
  --package-root backend/onedrive_map --command "python server.py" --language python --tools "*"

# Agents: Project Searcher first, because RFQ Assistant uses it as a collaborator.
# project_searcher.yaml lists the ContentIQ tool as __CONTENTIQ_WXO_TOOL__; the deploy script fills it in from .env.
sed "s/__CONTENTIQ_WXO_TOOL__/$CONTENTIQ_WXO_TOOL/" wxo/project_searcher.yaml > /tmp/project_searcher.yaml
.venv/bin/orchestrate agents import -f /tmp/project_searcher.yaml
.venv/bin/orchestrate agents import -f wxo/rfq_assistant.yaml

# Ask through the API and see every tool call
.venv/bin/python wxo/ask.py rfq_assistant "What drive power did Bramhall Copper's 2021 Quebrada Azul Expansion use, and what did the 2016 Phase 1 use?"
```

## Limits

- Each ContentIQ search still covers the whole client-drive agent and returns its top 15 passages. `match_sources` can only drop results; it can't make the right project's files appear. The one-line sample files name their project, which makes this look better than it will be on real documents.
- The map is a snapshot. Rebuild and re-upload it when the drive changes. In production the server would read a live map from the backend that syncs with Microsoft Graph.
- A personal OneDrive account can't register an Entra app to read the drive through Microsoft Graph, so the demo builds the map from the local copy in `synthetic_data/files_system_example`. A work tenant (SharePoint) would need an app registered by its IT (`Sites.Selected`).

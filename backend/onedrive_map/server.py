"""onedrive_map MCP server: folder-map tools for the RFQ agents in watsonx Orchestrate.

watsonx Orchestrate runs this file itself as a local MCP toolkit (stdio transport):
    orchestrate toolkits add --kind mcp --name onedrive_map --package-root backend/onedrive_map \
        --command "python server.py" --language python --tools "*"

Run it locally over HTTP for testing:
    python backend/onedrive_map/server.py --http   # http://127.0.0.1:8765/mcp
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from mcp.server.fastmcp import FastMCP  # noqa: E402

import folder_map  # noqa: E402

mcp = FastMCP(
    "onedrive_map",
    instructions=(
        "Folder map of the client OneDrive (Clients/<client>/<year>_<project>/<files>). "
        "Use it to find a project's folder and files, then to check which ContentIQ search "
        "results come from that project's files."
    ),
    host="127.0.0.1",
    port=8765,
)


@mcp.tool()
def find_projects(query: str = "", client: str = "", year_from: int | None = None,
                  year_to: int | None = None, limit: int = 10) -> dict:
    """Find project folders in the client OneDrive.

    Args:
        query: Words from the project name, site, scope or document code, e.g. "Quebrada Azul expansion" or "QAZ".
        client: Optional client name, e.g. "Bramhall Copper".
        year_from: Optional earliest project year (inclusive).
        year_to: Optional latest project year (inclusive).
        limit: Maximum number of projects to return.

    Returns projects (project_path, client, project, year, file_count), best match first, then newest first.
    """
    return folder_map.find_projects(query, client, year_from, year_to, limit)


@mcp.tool()
def list_folder(path: str = "") -> dict:
    """List the subfolders and files directly inside one OneDrive folder.

    Args:
        path: Folder path such as "Clients" or "Clients/Bramhall_Copper". Empty lists the Clients folder.
    """
    return folder_map.list_folder(path)


@mcp.tool()
def list_project_files(project_path: str) -> dict:
    """List every file in one project folder, with dates, plus search keywords for ContentIQ.

    Args:
        project_path: The project_path returned by find_projects, e.g. "Clients/Bramhall_Copper/2021_Quebrada_Azul_Expansion".

    Returns the files (name, path, modified, size), a search_phrase and search_keywords to put in ContentIQ queries.
    """
    return folder_map.list_project_files(project_path)


@mcp.tool()
def match_sources(project_path: str, source_names: list[str]) -> dict:
    """Check which ContentIQ search results belong to one project.

    ContentIQ returns file names without folders. This tool compares them with the project's files.

    Args:
        project_path: The project_path returned by find_projects.
        source_names: File names from the ContentIQ search results, e.g. ["QAZ-21-RFQ-01.txt", "QAZ-18-RFQ-02.txt"].

    Returns keep (from this project), drop (other projects or unknown), and details with each file's folder paths.
    """
    return folder_map.match_sources(project_path, source_names)


@mcp.tool()
def map_info() -> dict:
    """Show where the folder map came from, when it was built, and how many clients, projects and files it holds."""
    return folder_map.map_info()


if __name__ == "__main__":
    mcp.run(transport="streamable-http" if "--http" in sys.argv else "stdio")

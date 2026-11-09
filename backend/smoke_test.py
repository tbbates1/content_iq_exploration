#!/usr/bin/env python3
"""Start the onedrive_map MCP server over stdio (as watsonx Orchestrate does) and call each tool once."""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

SERVER = Path(__file__).resolve().parent / "onedrive_map" / "server.py"

CALLS = [
    ("map_info", {}),
    ("find_projects", {"query": "Quebrada Azul", "client": "Bramhall Copper"}),
    ("find_projects", {"query": "azula expansion", "year_from": 2017, "year_to": 2019}),
    ("list_folder", {"path": "Clients/Bramhall_Copper"}),
    ("list_project_files", {"project_path": "Clients/Bramhall_Copper/2021_Quebrada_Azul_Expansion"}),
    ("match_sources", {"project_path": "Clients/Bramhall_Copper/2021_Quebrada_Azul_Expansion",
                       "source_names": ["QAZ-21-RFQ-01.txt", "QAZ-18-RFQ-01.txt", "unknown.pdf"]}),
]


def short(obj: dict, n: int = 500) -> str:
    text = json.dumps(obj, ensure_ascii=False)
    return text if len(text) <= n else text[:n] + " ..."


async def main() -> int:
    params = StdioServerParameters(command=sys.executable, args=[str(SERVER)])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            print("tools:", ", ".join(t.name for t in tools.tools))
            failures = 0
            for name, args in CALLS:
                result = await session.call_tool(name, args)
                payload = result.structuredContent or json.loads(result.content[0].text)
                payload = payload.get("result", payload)
                bad = result.isError or "error" in payload
                failures += bad
                print(f"\n{'FAIL' if bad else 'ok  '} {name}({short(args, 200)})\n     {short(payload)}")
            return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

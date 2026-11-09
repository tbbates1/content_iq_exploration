#!/usr/bin/env python3
"""Ask a watsonx Orchestrate agent a question through the API and print every tool call.

Usage:
    .venv/bin/python wxo/ask.py rfq_assistant "What drive power did Bramhall Copper's 2021 Quebrada Azul Expansion use?"
    .venv/bin/python wxo/ask.py project_searcher "..." --raw run.json   # also save the thread messages

Reads WXO_API_KEY and WXO_SERVICE_URL from .env. Never prints the key.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

import requests

REPO = Path(__file__).resolve().parent.parent


def load_env() -> None:
    for line in (REPO / ".env").read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())


def iam_token(api_key: str) -> str:
    r = requests.post(
        "https://iam.cloud.ibm.com/identity/token",
        data={"grant_type": "urn:ibm:params:oauth:grant-type:apikey", "apikey": api_key},
        timeout=30,
    )
    r.raise_for_status()
    return r.json()["access_token"]


def short(value, n: int = 300) -> str:
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
    return text if len(text) <= n else text[:n] + " ..."


def summarize_tool_response(name: str, content: str) -> str:
    """ContentIQ responses are ~26k characters; show only the passage sources."""
    if name.startswith("symplisticai_tool"):
        try:
            r = json.loads(content)
            rag = (r.get("answer_context") or {}).get("unstructured_rag") or []
            sources = [x.get("source") for x in rag if isinstance(x, dict)]
            return f"{len(sources)} passages from: {sorted(set(sources))}"
        except (ValueError, AttributeError):
            pass
    return short(content)


def print_steps(messages: list[dict], indent: str = "") -> None:
    for m in messages:
        if m.get("role") == "user":
            continue
        for step in m.get("step_history") or []:
            for d in step.get("step_details", []):
                if d.get("type") == "tool_calls":
                    for c in d.get("tool_calls", []):
                        print(f"{indent}→ {c.get('name')}({short(c.get('args'), 400)})")
                elif d.get("type") == "tool_response":
                    print(f"{indent}  ← {summarize_tool_response(d.get('name', ''), d.get('content', ''))}")
                elif d.get("type") not in (None, "thinking", "tool_call"):
                    print(f"{indent}· {d.get('type')}: {short(d, 300)}")
        text = " ".join(c.get("text", "") for c in m.get("content") or [] if isinstance(c, dict))
        if text.strip():
            print(f"\n{indent}ANSWER ({m.get('assistant', {}).get('name', '') if isinstance(m.get('assistant'), dict) else ''}):\n{text}\n")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("agent", help="agent name, e.g. rfq_assistant")
    ap.add_argument("question")
    ap.add_argument("--raw", type=Path, help="save the thread messages as JSON")
    ap.add_argument("--timeout", type=int, default=300)
    args = ap.parse_args()

    load_env()
    base = os.environ["WXO_SERVICE_URL"].rstrip("/")
    headers = {"Authorization": f"Bearer {iam_token(os.environ['WXO_API_KEY'])}"}

    agents = requests.get(f"{base}/v1/orchestrate/agents", headers=headers, timeout=30).json()
    agents = agents if isinstance(agents, list) else agents.get("data", agents.get("agents", []))
    agent = next((a for a in agents if a.get("name") == args.agent), None)
    if agent is None:
        print(f"agent {args.agent!r} not found", file=sys.stderr)
        return 1

    start = time.time()
    run = requests.post(
        f"{base}/v1/orchestrate/runs",
        headers=headers,
        json={"agent_id": agent["id"], "message": {"role": "user", "content": args.question}},
        timeout=60,
    )
    run.raise_for_status()
    run = run.json()
    status = "running"
    while time.time() - start < args.timeout:
        status = requests.get(f"{base}/v1/orchestrate/runs/{run['run_id']}", headers=headers, timeout=30).json().get("status")
        if status in ("completed", "failed", "cancelled"):
            break
        time.sleep(4)
    messages = requests.get(f"{base}/v1/orchestrate/threads/{run['thread_id']}/messages", headers=headers, timeout=30).json()
    if args.raw:
        args.raw.write_text(json.dumps(messages, indent=1, ensure_ascii=False))

    print(f"agent: {args.agent}  status: {status}  time: {time.time() - start:.0f}s  thread: {run['thread_id']}")
    print(f"Q: {args.question}\n")
    print_steps(messages)
    return 0 if status == "completed" else 1


if __name__ == "__main__":
    sys.exit(main())

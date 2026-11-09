#!/usr/bin/env bash
# Deploy the RFQ demo to watsonx Orchestrate:
#   1. build the folder map from sample_drive/Clients and smoke-test the MCP server,
#   2. upload backend/onedrive_map as the onedrive_map toolkit (wxO hosts it, stdio),
#   3. import the project_searcher agent (with your ContentIQ search tool) and the rfq_assistant agent.
#
# Needs .env with WXO_API_KEY, WXO_SERVICE_URL and CONTENTIQ_WXO_TOOL (see .env.example). Optional: WXO_ENV.
# Safe to re-run: it replaces the toolkit and updates the agents.
set -euo pipefail
cd "$(dirname "$0")/.."

set -a; source .env; set +a
: "${WXO_API_KEY:?Set WXO_API_KEY in .env}"
: "${WXO_SERVICE_URL:?Set WXO_SERVICE_URL in .env}"
: "${CONTENTIQ_WXO_TOOL:?Set CONTENTIQ_WXO_TOOL in .env (.venv/bin/orchestrate tools list -v | grep -oE 'symplisticai_tool[a-z0-9_]*' | sort -u)}"
ENV_NAME="${WXO_ENV:-wxo}"
PY=.venv/bin/python
ORCH=.venv/bin/orchestrate

echo "== Folder map"
$PY backend/build_map.py
if ! out="$($PY backend/smoke_test.py 2>/dev/null)"; then echo "$out"; echo "smoke test failed" >&2; exit 1; fi
echo "smoke test passed"

echo "== ADK environment: $ENV_NAME"
if ! $ORCH env list 2>/dev/null | grep -qE "^[[:space:]]*${ENV_NAME}[[:space:]]"; then
  $ORCH env add -n "$ENV_NAME" -u "$WXO_SERVICE_URL" --type ibm_iam
fi
$ORCH env activate "$ENV_NAME" --api-key "$WXO_API_KEY" > /dev/null

if ! $ORCH tools list -v 2>/dev/null | grep -q "\"$CONTENTIQ_WXO_TOOL\""; then
  echo "ContentIQ tool $CONTENTIQ_WXO_TOOL not found in $ENV_NAME. Check CONTENTIQ_WXO_TOOL in .env." >&2
  exit 1
fi

echo "== Toolkit: onedrive_map"
if $ORCH toolkits list 2>/dev/null | grep -q "onedrive_map"; then
  $ORCH toolkits remove -n onedrive_map
fi
$ORCH toolkits add --kind mcp --name onedrive_map \
  --description "Folder map of the client OneDrive" \
  --package-root backend/onedrive_map --command "python server.py" --language python --tools "*"

echo "== Agents"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
sed "s/__CONTENTIQ_WXO_TOOL__/${CONTENTIQ_WXO_TOOL}/" wxo/project_searcher.yaml > "$tmp/project_searcher.yaml"
$ORCH agents import -f "$tmp/project_searcher.yaml"   # first: rfq_assistant uses it as a collaborator
$ORCH agents import -f wxo/rfq_assistant.yaml

echo "Done. Try: $PY wxo/ask.py rfq_assistant \"What drive power, pole count and supply voltage are in the RFQs for Bramhall Copper's 2021 Quebrada Azul Expansion?\""

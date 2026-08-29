#!/usr/bin/env bash
# Dogfood: scan this repo's agent MCP configs on every commit + CI.
# Uses mcphound once it exists; falls back to mcp-scan (Invariant/Snyk) meanwhile.
set -uo pipefail

CONFIGS=".mcp.json opencode.jsonc opencode.json"
FOUND=0

if command -v mcphound >/dev/null 2>&1 || [ -x "./venv/bin/mcphound" ]; then
  for f in $CONFIGS; do
    [ -f "$f" ] || continue
    echo "[self-scan] mcphound scan $f"
    uv run mcphound scan "$f" --json --fail-on high || exit 1
  done
elif command -v mcp-scan >/dev/null 2>&1; then
  echo "[self-scan] mcphound not installed yet, using mcp-scan interim"
  mcp-scan .mcp.json --json || exit 1
else
  echo "[self-scan] WARN: no scanner available yet — install mcphound or run: uvx mcp-scan@latest"
  # Don't block commits in week 1; CI will run the real scan once mcphound exists.
  exit 0
fi

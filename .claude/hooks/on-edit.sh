#!/usr/bin/env bash
# Claude Code PostToolUse hook: auto-format/lint Python files on edit.
# Never fails the agent's turn (exit 0) — formatting is best-effort.
set -euo pipefail

input=$(cat)
file=$(echo "$input" | python3 -c '
import sys, json
try:
    d = json.load(sys.stdin)
    print(d.get("tool_input", {}).get("file_path", ""))
except Exception:
    print("")
' 2>/dev/null || true)

case "$file" in
  *.py)
    if command -v ruff >/dev/null 2>&1; then
      ruff check --fix "$file" >/dev/null 2>&1 || true
      ruff format "$file" >/dev/null 2>&1 || true
    fi
    ;;
esac

exit 0

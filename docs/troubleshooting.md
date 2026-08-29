Setup troubleshooting
Claude Code warnings on first launch
"Server X is defined in multiple scopes with different endpoints"
You installed a server at user scope earlier (unpinned, e.g. npx -y @upstash/context7-mcp) and the project also defines it in .mcp.json (pinned, e.g. @upstash/context7-mcp@1.0.0). Keep the project-scoped pinned version — that's the supply-chain control — and remove the user-scope duplicates:

Bash

claude mcp remove context7 -s user
claude mcp remove postgres -s user
Then run /mcp inside Claude Code to verify each server shows once and connects.

"Missing environment variables: MCPHOUND_DATABASE_URL_RO"
The postgres MCP server needs a database DSN. You don't need it until Phase 3
(week 10+, reputation DB work) — it is intentionally NOT in .mcp.json at the
start, so this warning should disappear after the scope cleanup above.

When you do reach Phase 3, add the server to .mcp.json and put the secret in
the gitignored .claude/settings.local.json, never in .mcp.json:

JSON

{
  "env": {
    "MCPHOUND_DATABASE_URL_RO": "postgresql://mcphound_ro:password@localhost:5432/mcphound_dev"
  }
}
Claude Code applies the env block to the session and spawned MCP servers
inherit it. Windows PowerShell alternative (persistent user env var):

PowerShell

[Environment]::SetEnvironmentVariable("MCPHOUND_DATABASE_URL_RO","postgresql://mcphound_ro:password@localhost:5432/mcphound_dev","User")
Restart the terminal and Claude Code after setting it.

Windows notes
The PostToolUse ruff hook (.claude/hooks/on-edit.sh) is a bash script.
It runs if Git Bash or WSL is on your PATH; if not, it simply doesn't fire —
it's best-effort and never blocks. Ruff also runs in pre-commit and CI, so
you're covered either way.
Use PowerShell or Git Bash for the Makefile commands; if make is
unavailable, run the underlying commands directly:
uv sync --extra dev, uv run pytest -q, uv run ruff check .
Line endings: let git keep LF for shell scripts
(git config core.autocrlf input recommended).
General MCP server checks
/mcp in Claude Code shows connection state per server.
Test a server in isolation before adding it: npx -y <package> --help or the
MCP Inspector (npx @modelcontextprotocol/inspector <command>).
Never pin to @latest in committed configs — bump versions deliberately and
note the bump in the commit message.

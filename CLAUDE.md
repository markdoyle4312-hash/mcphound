# mcpvet — project rules for AI coding agents

> This file is read by Claude Code automatically, and by OpenCode via `instructions: ["./CLAUDE.md"]` in opencode.json. Keep it short — long procedures go in `.claude/skills/` and `.opencode/skills/`.

## What we're building
Independent security reputation + policy-enforcement layer for MCP servers and agent skills. Three surfaces:
1. **Scanner CLI** (`mcpvet`): discovers MCP configs, static + dynamic analysis, SARIF/JSON output.
2. **Reputation DB + site/API**: continuous scanning of the public MCP registry; per-server risk pages.
3. **Enforcement**: GitHub Action + `mcp-policy.yaml` allowlist enforcement.

## Stack
- Python 3.12, Typer CLI, `mcp` official SDK, FastAPI (API), Postgres, Docker for dynamic sandboxing.
- Website: Next.js (separate `site/` directory later).
- Package management: `uv`. Tests: `pytest`. Lint/format: `ruff`.

## Non-negotiable engineering rules
- **Every detection rule ships with**: a YAML rule file, a malicious fixture, a benign fixture (false-positive guard), and a pytest. No rule without all four.
- Rules are data, not code: add detections in `src/mcpvet/rules/*.yaml` using the rule schema (see skill `rule-authoring`).
- Every finding maps to an OWASP code (LLM Top 10 / Agentic-MCP Top 10). No uncategorized findings.
- Output must be deterministic in CI: `--json` and SARIF modes print no spinner/emojis.
- Tests must pass before you say a task is done. Run `uv run pytest -q`.

## SAFETY RULES (this project handles malware-adjacent code — read twice)
- **Never execute a fixture MCP server on the host.** No `npx`, `uvx`, `node`, or `python` against anything in `tests/fixtures/` outside Docker. Dynamic analysis runs only via the sandbox runner (`docker` with a dedicated egress-proxy network, no mounted secrets, no host network).
- Every malicious fixture contains the canary marker string `MCPVET-FIXTURE-CANARY` and is never referenced from `.mcp.json`, `opencode.json`, or any agent config.
- Do not add new MCP servers to agent configs without: (a) pinned version, (b) a note in this commit message why it's needed, (c) running `mcpvet scan` (or mcp-scan as interim) against the changed config.
- Never put secrets in config files; use environment variables only (`.env`, gitignored).
- `git push`, package publishes, and `docker run` require explicit human approval — they are set to "ask" in both tools' permissions.

## Conventions
- Conventional commits (`feat:`, `fix:`, `rule:`, `docs:`). Rule additions use `rule: MCP-0xx ...`.
- New public CLI flags need a docs update in the same PR.
- When researching attacks, prefer primary sources (Invariant Labs disclosures, CSA papers, OWASP, CVEs); cite URLs in code comments or PR descriptions.

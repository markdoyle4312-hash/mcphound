# mcpvet

Independent security scanner and reputation layer for MCP servers and agent skills.

> Status: **pre-launch.** v0.1 = static CLI scanning. Reputation site/API and the GitHub Action follow per [ROADMAP.md](ROADMAP.md).

mcpvet discovers the MCP servers configured in your AI coding clients (Claude Code/Desktop, Cursor, Windsurf, Gemini CLI, OpenCode) and checks them for supply-chain risks: hardcoded secrets, download-and-execute launch commands, over-broad permissions, pinned-version drift, and (in later versions) tool-description poisoning, typosquats, and runtime rug-pulls. Findings map to the OWASP Top 10 for LLM and Agentic applications and can be exported as SARIF into GitHub code scanning.

## Why another scanner?

Local scanning is covered by [mcp-scan](https://github.com/invariantlabs-ai/mcp-scan) / Snyk Agent Scan. mcpvet's job is the layers around it:

1. A **public reputation database** — continuously scanned public registry, per-server risk pages and change history.
2. **Org-level enforcement** — `mcp-policy.yaml` + GitHub Action that blocks risky MCP/skill changes in PRs.
3. **Compliance reporting** — findings mapped to OWASP, EU AI Act, and (later) Australian ISM / Essential Eight / DISP controls.

## Quickstart

```bash
# published on PyPI as "mcphound" (mcpvet and mcp-vet were both already
# taken/rejected) — mcphound is also installed as the "mcpvet" command,
# kept as a back-compat alias
uvx mcphound inspect   # inspect what you have (never executes a server)
uvx mcphound scan      # scan auto-discovered configs

# or install once:
# pip install mcphound / uv tool install mcphound

# CI: fail on high/critical findings, emit SARIF
mcphound scan .mcp.json --fail-on high --sarif -o mcphound.sarif

# opt-in: also run network-dependent checks (npm registry provenance) — slower,
# not fully deterministic offline, so it's off unless you ask for it
mcphound scan --deep
```

## Development

```bash
uv sync --extra dev
uv run pytest -q          # tests
uv run ruff check .       # lint
make scan-self            # scan this repo's own agent configs (dogfood)
```

## Safety

mcpvet static scanning **never executes** MCP servers. Dynamic analysis (post-v1) runs only inside the disposable, network-isolated sandbox in `sandbox/`. Every malicious test fixture carries the marker `MCPVET-FIXTURE-CANARY` and must never be referenced from agent configurations.

## Authoring a detection rule

Every rule ships with four artifacts: YAML rule, malicious fixture, benign fixture, pytest. See `.claude/skills/rule-authoring/SKILL.md` (or the two worked examples under `src/mcpvet/rules/` and `tests/`).

## License

Apache-2.0

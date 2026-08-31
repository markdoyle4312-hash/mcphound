# mcphound

Independent security scanner and reputation layer for MCP servers and agent skills.

> Status: **v0.1 published** ([PyPI](https://pypi.org/project/mcphound/)) — static CLI scanning, a local registry poller/scorer, a read-only reputation API, and a Next.js site are built; none of the site/API is deployed publicly yet, and the GitHub Action / policy enforcement is still ahead. See [ROADMAP.md](ROADMAP.md).

mcphound discovers the MCP servers configured in your AI coding clients (Claude Code/Desktop, Cursor, Windsurf, Gemini CLI, OpenCode) and checks them for supply-chain risks: hardcoded secrets, download-and-execute launch commands, over-broad permissions, pinned-version drift, and (in later versions) tool-description poisoning, typosquats, and runtime rug-pulls. Findings map to the OWASP Top 10 for LLM and Agentic applications and can be exported as SARIF into GitHub code scanning.

## Why another scanner?

Local scanning is covered by [mcp-scan](https://github.com/invariantlabs-ai/mcp-scan) / Snyk Agent Scan. mcphound's job is the layers around it:

1. A **public reputation database** — continuously scanned public registry, per-server risk pages and change history.
2. **Org-level enforcement** — `mcp-policy.yaml` + GitHub Action that blocks risky MCP/skill changes in PRs.
3. **Compliance reporting** — findings mapped to OWASP, EU AI Act, and (later) Australian ISM / Essential Eight / DISP controls.

## Quickstart

```bash
# published on PyPI as "mcphound"
uvx mcphound inspect   # inspect what you have (never executes a server)
uvx mcphound scan      # scan auto-discovered configs

# or install once:
# pip install mcphound / uv tool install mcphound

# CI: fail on high/critical findings, emit SARIF
mcphound scan .mcp.json --fail-on high --sarif -o mcphound.sarif

# CI dry-run: report findings without failing the build — drop --fail-on
# and the exit code stays 0 regardless of severity, so you can preview
# what a policy would catch before you start enforcing it
mcphound scan .mcp.json --json -o mcphound-preview.json

# opt-in: also run network-dependent checks (npm registry provenance) — slower,
# not fully deterministic offline, so it's off unless you ask for it
mcphound scan --deep

# dogfood: scan only this project's own configs (.mcp.json, opencode.json[c] in
# the current directory), skipping user-level client configs — for CI/pre-commit
mcphound scan --self --fail-on high
```

Full rule catalog with OWASP mappings: [docs/rules.md](docs/rules.md).

## Reporting a false positive

```bash
mcphound feedback MCP-STATIC-004 --note "why you think this is wrong"
```

Prints a pre-filled GitHub issue URL — no network call, no auth. Redact secrets
from any config snippet before pasting it into the issue. See
[GOVERNANCE.md](GOVERNANCE.md#false-positives) for the full policy.

## Allowlist enforcement

```bash
mcphound allowlist init      # bootstrap mcp-policy.yaml + a findings baseline
mcphound allowlist enforce   # fail the build on unlisted servers or new findings
```

Declares which MCP servers a repo expects and enforces it — `mode: baseline`
(the `init` default) only fails on *new* findings, not ones already present
when the baseline was written. See [docs/policy.md](docs/policy.md).

## GitHub Action

Enforces `mcp-policy.yaml` on every pull request — posts a sticky risk
report comment and fails the check on a violation. See
[docs/action.md](docs/action.md) for setup.

## Registry poller (local, opt-in)

Ingests the official MCP Registry into a local Postgres database for future
reputation-scoring work. Not needed to use `mcphound scan`/`inspect`/`feedback`
— see [docs/registry-poller.md](docs/registry-poller.md) for setup.

## Read-only API (local, opt-in)

A free, rate-limited JSON API + embeddable badge over the scored registry
data — `GET /v1/servers/{slug}`, `GET /v1/check?name=`, `GET
/v1/badge/{slug}.svg`. See [docs/api.md](docs/api.md) for the full
reference and how to run it locally.

## Development

```bash
uv sync --extra dev
uv run pytest -q          # tests
uv run ruff check .       # lint
make scan-self            # scan this repo's own agent configs (dogfood)
make docs                 # regenerate docs/rules.md from the rule YAML files
```

## Safety

mcphound static scanning **never executes** MCP servers. Dynamic analysis (post-v1) runs only inside the disposable, network-isolated sandbox in `sandbox/`. Every malicious test fixture carries the marker `MCPHOUND-FIXTURE-CANARY` and must never be referenced from agent configurations.

## Authoring a detection rule

Every rule ships with four artifacts: YAML rule, malicious fixture, benign fixture, pytest. See `.claude/skills/rule-authoring/SKILL.md` (or the two worked examples under `src/mcphound/rules/` and `tests/`).

## License

Apache-2.0

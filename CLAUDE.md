# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

> This file is read by Claude Code automatically, and by OpenCode via `instructions: ["./CLAUDE.md"]` in opencode.json. Keep it short — long procedures go in `.claude/skills/` and `.opencode/skills/`.

## What we're building
Independent security reputation + policy-enforcement layer for MCP servers and agent skills. Three surfaces:
1. **Scanner CLI** (`mcphound`, published on PyPI): discovers MCP configs, static analysis, JSON/SARIF output.
2. **Reputation DB + site/API**: continuous scanning of the public MCP registry; per-server risk pages (`site/`, static Next.js export on Cloudflare Pages).
3. **Enforcement**: GitHub Action (`action.yml`) + `mcp-policy.yaml` allowlist enforcement.

See `ROADMAP.md` for milestone status (what's shipped vs. still open) and `README.md` for user-facing usage.

## Stack
- Python 3.12, Typer CLI, Pydantic, PyYAML, httpx. SQLAlchemy + Alembic + Postgres (`registry` extra), FastAPI + slowapi (`api` extra) — both optional, kept out of the core install so `pip install mcphound` stays lightweight.
- Website: Next.js 16 (App Router, static export) in `site/`, Vitest + ESLint, deployed nightly to Cloudflare Pages.
- Package management: `uv` (Python), `npm` (site/). Tests: `pytest` / `vitest`. Lint/format: `ruff` / `eslint`. Types: `mypy`.

## Commands

```bash
# Python (repo root)
uv sync --extra dev                 # base + dev deps
uv sync --all-extras                # + registry (sqlalchemy/alembic/psycopg) + api (fastapi)
uv run pytest -q                    # all tests
uv run pytest tests/test_rules.py -q -k MCP-STATIC-004   # a single rule's test
uv run pytest tests/db tests/registry tests/api -q       # DB-backed tests (need a running Postgres; see db-up)
uv run ruff check .                 # lint
uv run ruff format .                # format
make typecheck                      # mypy src/mcphound, with registry+api extras so those modules type-check too
make scan-self                      # dogfood: mcphound scan --self --fail-on high
make docs                           # regenerate docs/rules.md from src/mcphound/rules/*.yaml
make docs-check                     # CI guard: fails if docs/rules.md is stale
make rules-check                    # CI guard: fails if any rule is missing a fixture/test
make db-up                          # local Postgres via docker compose, for registry-poll/registry-scan work
make db-migrate                     # alembic upgrade head

# Next.js site (site/)
cd site && npm ci
npm test                            # vitest
npm run lint                        # eslint
npm run prepare:sample-data         # copy site/test-fixtures/sample-data into place for a local/CI build
npm run build                       # static export (runs prebuild: scripts/build-server-shards.ts)
```

CI (`.github/workflows/ci.yml`) runs five independent jobs: `test` (lint+mypy+pytest+SARIF smoke test), `self-scan` (dogfood), `docs-check`, `db-tests` (real Postgres service container), `site-build`. Match a job locally with the commands above before pushing.

## High-level architecture

**Static scan pipeline** (`mcphound scan`/`inspect`/`allowlist enforce`, the CLI-only path with no DB dependency):
`discovery/clients.py` finds and parses MCP config files across 5 clients (Claude Desktop/Code, Cursor, Windsurf, Gemini CLI, OpenCode) into `ServerConfig` objects (`models.py`) → `rules/loader.py` loads YAML rules from `rules/*.yaml` → `rules/engine.py` evaluates each rule against each server (`evaluate()`, one finding per rule per server) → `output.py` renders `ScanResult` as text/JSON/SARIF. `cli.py`'s `_collect()` is the shared entry point all scan-like commands go through; it filters out `network: true` rules unless `--deep` is passed.

**Rule engine (`rules/engine.py`) detect-block shapes** — a rule is YAML data, not code, but its `detect.type` selects one of a fixed set of engine-side evaluators: default regex (`target` + `pattern` + optional `allow_if`), `typosquat` (Levenshtein distance against a bundled reference list in `rules/data/`), `npm_provenance`/`npm_install_script`/`registry_age` (network calls to npm/PyPI, always `network: true`, gated behind `--deep`), plus a secondary `also: oci_pin` check for unpinned `docker run` images that runs only when the primary check found nothing. The module docstring in `rules/engine.py` is the authoritative reference for this schema — read it before adding a rule, alongside the `rule-authoring` skill.

**Policy/allowlist path** (`policy.py`): `allowlist init` snapshots the current scan into `mcp-policy.yaml` (server identities + pinned versions/digests) and a findings baseline; `allowlist enforce` re-scans and diffs against both, so `mode: baseline` only fails on *new* findings, not ones already present when the baseline was written. This is what `action.yml` runs on every PR via `uvx mcphound`.

**Registry/reputation path** (`registry` extra, DB-backed, separate from the static-scan path above): `registry/poller.py` pages the public MCP Registry API into Postgres (`db/models.py`, migrated via `alembic/`) → `registry/scanner.py` batch-runs the same rule engine across every registry server, concurrently (network-bound) → `registry/scoring.py` computes a 0–100 score per server → `registry/artifacts.py` writes per-server JSON + a sharded index to disk for the site to consume statically (not a live API call per page — see ROADMAP.md's W14 sharding note for why: Vercel/Cloudflare per-deployment file-count caps forced sharding registry data into 64 fixed JSON files instead of one static page per server). `api/app.py` (the `api` extra) is a separate, optional read path over the same DB (`GET /v1/servers/{slug}`, `/v1/check`, `/v1/badge/{slug}.svg`), not something `registry-scan`/artifacts generation depends on.

**Site (`site/`)**: static Next.js export, not a web app with a live backend. `lib/data.ts` reads the sharded JSON in `data/`/`public/data/` (populated by `registry-export`/`registry-scan` or, for local dev/CI, `npm run prepare:sample-data` from `test-fixtures/sample-data/`). `scripts/build-server-shards.ts` runs as `prebuild`. Deployed nightly via `.github/workflows/nightly.yml`.

**CLI module-loading pattern** (`cli.py`): `registry-poll`/`registry-scan`/`registry-export` commands import sqlalchemy-backed modules inside a try/except so the base `mcphound` install (no `registry` extra) doesn't crash on import; each such command calls `_require_registry_extra()` to fail with a clear message instead of a raw `ModuleNotFoundError`. Follow this pattern for any new command that needs an optional extra.

## Non-negotiable engineering rules
- **Every detection rule ships with**: a YAML rule file, a malicious fixture, a benign fixture (false-positive guard), and a pytest. No rule without all four.
- Rules are data, not code: add detections in `src/mcphound/rules/*.yaml` using the rule schema (see skill `rule-authoring`).
- Every finding maps to an OWASP code (LLM Top 10 / Agentic-MCP Top 10). No uncategorized findings.
- Output must be deterministic in CI: `--json` and SARIF modes print no spinner/emojis.
- Tests must pass before you say a task is done. Run `uv run pytest -q`.

## SAFETY RULES (this project handles malware-adjacent code — read twice)
- **Never execute a fixture MCP server on the host.** No `npx`, `uvx`, `node`, or `python` against anything in `tests/fixtures/` outside Docker. mcphound is static-analysis only today — the Docker sandbox runner (dedicated egress-proxy network, no mounted secrets, no host network) is unbuilt scaffolding (see `sandbox/README.md`, ROADMAP.md's v1.5 milestone). Dynamic analysis MUST NOT run anywhere except that sandbox once it exists; until then, don't execute untrusted or fixture servers at all.
- Every malicious fixture contains the canary marker string `MCPHOUND-FIXTURE-CANARY` and is never referenced from `.mcp.json`, `opencode.json`, or any agent config.
- Do not add new MCP servers to agent configs without: (a) pinned version, (b) a note in this commit message why it's needed, (c) running `mcphound scan` (or mcp-scan as interim) against the changed config.
- Never put secrets in config files; use environment variables only (`.env`, gitignored).
- `git push`, package publishes, and `docker run` require explicit human approval — they are set to "ask" in both tools' permissions.

## Conventions
- Conventional commits (`feat:`, `fix:`, `rule:`, `docs:`). Rule additions use `rule: MCP-0xx ...`.
- New public CLI flags need a docs update in the same PR.
- When researching attacks, prefer primary sources (Invariant Labs disclosures, CSA papers, OWASP, CVEs); cite URLs in code comments or PR descriptions.

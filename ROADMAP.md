# mcphound — v1 Timeline & Roadmap

---

## What "v1.0 deployment" means (and doesn't)

**v1.0 is three things live:**
1. **CLI published** — PyPI/`uvx`, static scanning works, `--json` + SARIF output, `scan` + `inspect` commands.
2. **Reputation site + API live** — first batch of real public-registry MCP servers scanned, spot-checked, with per-server score pages and a rate-limited API.
3. **GitHub Action in the Marketplace** — enforces `mcp-policy.yaml` on PRs.

**Explicitly NOT in v1.0 (post-launch):** dynamic sandbox (egress logging, runtime rug-pull detection), LLM analysis mode, auth/accounts/team tier, remote HTTP server deep-scanning. These are v1.2–v2.0 differentiators, not launch requirements.

---

## Milestone timeline

| Milestone | Contents |
|---|---|
| **v0.1 — public CLI** | Config discovery (5 clients), rule engine, ~8 static rules, fixtures, pytest, PyPI/GitHub publish |
| v0.2 — hardening | FP passes vs top 50 real servers, docs/README, first Show HN / r/mcp post |
| **v1.0-beta — reputation site + API** | Registry poller, Postgres, FastAPI, static-generated score pages, badge, rate-limited API, ~1,000 servers scored & spot-checked |
| **v1.0 — enforcement + launch** | GitHub Action + `mcp-policy.yaml`, Marketplace listing, "State of MCP Security" report |
| v1.5 — dynamic sandbox | Docker sandbox runner, egress proxy, description-hash drift alerts |

AI-assisted coding makes the scaffolding fast; most of the time goes to MCP SDK edge cases, false-positive tuning, and site/infra glue.

---

## Week-by-week plan (each session has a defined "done")

### Phase 1 — v0.1 public CLI

- [x] **W1** — Repo init: copy scaffold, `pyproject.toml` (uv, typer, mcp SDK, pydantic, pytest, ruff), CLAUDE.md in place, CI green on empty tests. *Done: `uv run pytest` passes with 1 trivial test; repo public.*
- [x] **W2** — Config discovery: parsers for Claude Desktop/Code, Cursor, Windsurf, Gemini CLI paths; `inspect` command lists servers without executing. *Done: `mcphound inspect` lists servers on your own machine; tests with sample configs.*
- [x] **W3** — Rule engine v1: YAML rule loader, findings dataclass, JSON output; first 4 static rules (hardcoded secrets in config, dangerous launch commands/curl-pipe-shell, over-broad filesystem/shell permissions, pinned-version check). *Done: each rule has the 4 artifacts (YAML + malicious fixture + benign fixture + test) per the `rule-authoring` skill.*
- [x] **W4** — Tool-description injection markers (`MCP-STATIC-005`: hidden HTML comments, zero-width chars, exfiltration-imperative phrasing), typosquat distance vs a bundled name list (`MCP-STATIC-006`, Levenshtein via rapidfuzz), package provenance (`MCP-STATIC-007`, npm-only, scoped to a missing `repository` field). *Done: 7 rules passing, not the originally-targeted 8 — provenance covers 1 of the 3 sub-checks named above; postinstall-script inspection and registry-age checks are still open. Provenance is network-dependent, so it's marked `network: true` and gated behind `mcphound scan --deep`, off by default, per GOVERNANCE.md's separability rule. `--json` stays deterministic without `--deep`.*
- [x] **W5** — SARIF output + `--fail-on` exit codes + README with install/quickstart, `-o/--output` flag. Publish to PyPI; tag v0.1: **done** — `v0.1.0`/`v0.1.1`/`v0.1.2` tagged and pushed, published to PyPI as `mcphound` (the `mcpvet`/`mcp-vet` names were taken; the project renamed before publish — see the rename commits). `uvx mcphound scan <config>` works on a stranger's machine. Repo flipped to public on 2026-08-29 alongside a README fix (status line still said "pre-launch" after publish).
- [ ] **W6** — Launch post: Show HN, r/mcp, r/cybersecurity, X/LinkedIn; dogfood on your own `.mcp.json`. *Done: 100 stars target; collect first 5 issues.* Dogfood run 2026-08-29: `mcphound scan .mcp.json` on this repo — clean, no findings, verified against the published PyPI package from a fully clean environment. *Partial: r/mcp posted 2026-08-29 (showcase flair, disclosure line — see `LAUNCH_POST.md`'s "Before posting" checklist). Show HN attempt the same day was blocked by HN's anti-spam gate on accounts without history; deferred, no fixed retry date. r/cybersecurity, X, and LinkedIn still open.*

### Phase 2 — v0.2 hardening

- [x] **W7** — False-positive sweep: run against the 50 most-installed registry servers; tune severity/confidence; document every FP in CHANGELOG. *Done: swept 36 source-verified real servers (mcphound has no registry download-count data yet, so "50 most-installed" is a best-effort proxy — see `tests/fp_sweep/SOURCES.md`); zero false positives found; documented `MCP-STATIC-004`'s expected high real-world hit rate and `MCP-STATIC-007`'s three confirmed true positives; fixed a `MCP-STATIC-004` detection gap (`uvx --from`/`uv run --with` command shapes) the sweep surfaced; added `tests/fp_sweep/test_fp_sweep.py` as a permanent regression guard. 2026-08-29.*
- [x] **W8** — Docs site pass (usage, rule catalog with OWASP mappings, false-positive reporting flow); `mcphound scan --self` dogfood command. *Done: `docs/rules.md` generated from the rule YAML (`make docs`, CI-guarded against drift); `mcphound scan --self` scans only this project's own configs; `mcphound feedback <rule-id>` prints a pre-filled false-positive issue URL; README/GOVERNANCE.md updated. Also fixed a stale `__version__` and a Windows non-UTF-8 `read_text()` bug found along the way. 2026-08-29.*
- [ ] **W9** — Buffer/week: bugfixes from launch feedback, first external PRs, community rules process (`GOVERNANCE.md`). *Partial: the community rules process is done — GOVERNANCE.md now has a real proposal→review→merge process, `.github/PULL_REQUEST_TEMPLATE.md`, and `.github/ISSUE_TEMPLATE/new-rule-proposal.md`. Bugfixes-from-launch-feedback and first-external-PRs are still blocked on W6 (launch post), which hasn't happened yet — nothing to act on there. 2026-08-29.*

### Phase 3 — v1.0-beta reputation site + API

- [x] **W10–11** — Registry poller: ingest official MCP Registry API nightly + dedupe; Postgres schema (servers, versions, scans, findings, hashes). *Done: cron job populates DB locally.* `mcphound registry-poll --config config/registry.yaml` pages the real registry (confirmed live at registry.modelcontextprotocol.io, no delta API — full re-page every run) and upserts by natural key; soft-delist via `delisted_at` for anything no longer present. `hashes` is an append-only drift-detection ledger, not a 1:1 mirror of the registry's own hash. `scans`/`findings` tables exist, populated by W12-13. SQLAlchemy 2.0 + Alembic + docker-compose Postgres for local dev; `db-tests` CI job runs against a real Postgres service container. See `docs/registry-poller.md` for the full reasoning. 2026-08-29.*
- [x] **W12–13** — Batch static scanning pipeline over all ingested servers; scoring engine (weighted 0–100, OWASP-coded findings). *Done: full registry scanned to JSON artifacts — `mcphound registry-scan` ran against the live registry (2026-08-30): 25,273 servers scored, 821 flagged, scores 76-100 (avg 99.8), artifacts in `artifacts/servers/*.json` + `artifacts/index.json`. Along the way, fixed `registry-poll` pulling ~3.4x more rows than needed (missing `version=latest` filter) and a case-insensitive filename collision that was silently dropping 5 servers' artifacts — see CHANGELOG.md. Scores are not yet human-spot-checked (that's W16).*
- [x] **W14** — **Static site generator** (not a web app): per-server score pages from nightly snapshots, leaderboard, typosquat cluster pages. Deploy cheap (Vercel/Cloudflare Pages). *Done: Next.js site (leaderboard, paginated listing, per-server pages, typosquat watchlist) deploys nightly via `nightly.yml` — Vercel project `marksit/site` linked, `VERCEL_TOKEN`/`VERCEL_ORG_ID`/`VERCEL_PROJECT_ID` repo secrets set, `if: false` gate removed. Registry data now backed by a hosted Neon Postgres (`MCPHOUND_DATABASE_URL` repo secret, schema migrated via `alembic upgrade head`) since CI has no access to a local/dev DB — this didn't exist before today, `registry-poll`/`registry-scan` had only ever been run locally. Also fixed the job's `uv sync` missing `--all-extras`, which would have failed on the first real run (registry-poll needs the `registry` extra's SQLAlchemy/psycopg). 2026-08-30.*
- [ ] **W15** — FastAPI read-only API (`/v1/servers/{id}`, `/v1/check?name=`), rate-limited, free tier; embeddable badge for server authors. *Done: `GET /v1/servers/{slug}`, `GET /v1/check?name=`, and `GET /v1/badge/{slug}.svg` are implemented with slowapi rate limiting (60/min, 60/min, 300/min) and documented in `docs/api.md`. Shipped on PyPI in `v0.1.3` (opt-in via `pip install 'mcphound[api]'`); the FastAPI service itself still runs locally only — no public deployment yet. 2026-08-30.*
  - **Post-release hardening (2026-08-30, internal audit):** `.github/workflows/ci.yml` had a job-level `schedule:` key that isn't valid GitHub Actions syntax — it failed schema validation and silently ran **zero jobs** on every push/PR since it was added, so none of the work above (lint, tests, the API's own `db-tests` suite, the dogfood scan, the site build) had ever actually been confirmed by CI. Fixed, and CI is now green for real for the first time. That first real run immediately caught two genuine pre-existing bugs: (1) `mcphound scan`/`inspect`/`feedback` crashed with `ModuleNotFoundError: No module named 'sqlalchemy'` on a plain `pip install mcphound` — the CLI unconditionally imported the DB/registry stack instead of gating it behind the `registry` extra, now fixed; (2) a slug-lookup test assumed Python's string ordering matches Postgres's collation order, which isn't guaranteed — fixed to derive the expected order from the DB itself. Also fixed `registry/artifacts.py`'s typosquat-neighbor lookup silently dropping a server whenever two servers shared the same package identifier (a dict keyed by package instead of a list), added test coverage for `db/session.py`'s missing-DSN error path and `registry/config.py`'s default-value fallbacks, added ESLint to `site/` (Next.js 16 dropped the built-in `next lint`, leaving zero JS/TS lint coverage) wired into CI, and enabled branch protection on `main` + Dependabot alerts.
- [x] **W16** — **Manual spot-check sprint**: hand-verify scores on ~50 servers (credibility gate — a bad viral "it flagged a legit server" take costs more than delay). *Done: 50/50 servers hand-verified against live sources (MCP registry API, npm/PyPI, GitHub) — see `docs/spot-checks/w16-2026-08-30.md` for the full evidence trail. Sample was stratified, not random: all 4 servers hit by the rare `MCP-STATIC-003`/`004` rules, 31 random `MCP-STATIC-007` hits, 15 random clean (score-100) servers. Result: 0 false positives, 0 false negatives — every finding checked out against the real launch config/registry metadata. Surfaced two rule-quality follow-ups (not correctness bugs): `MCP-STATIC-007`'s message conflates "missing repository field" with "package fully unpublished from npm" (3/31 samples were actually unpublished, a more serious condition than the message implies); and a possible `MCP-STATIC-004` gap where a floating/non-semver OCI tag (`:mcp` rather than a pinned version) isn't caught as unpinned the way `@latest` is. Neither fixed as part of this review — logged for follow-up. 2026-08-30.* *Partial: the FP feedback button (`mcphound feedback <rule-id>`) shipped back in W8 — still not connected to a public-facing flow since the site isn't deployed yet (see W14).*
- [ ] **W17** — Buffer/week: infra hardening, monitoring, cost check.

### Phase 4 — v1.0 enforcement + launch

- [ ] **W18** — `mcp-policy.yaml` spec (allowed servers, pinned versions/hashes, max permissions, blocked registries) + CLI `allowlist init/enforce`.
- [ ] **W19** — GitHub Action: on PR, diff MCP/agent config + skill dirs, post markdown risk report, fail on policy violation; Marketplace listing. *Done: action runs on a demo repo with green/red examples.*
- [ ] **W20** — **"State of MCP Security" report**: aggregate real numbers (% no-auth, % dangerous permissions, typosquat count, rug-pulls observed).
- [ ] **W21** — Launch: report + v1.0 tag. Notify every server author with a badge. *Done: v1.0 deployed.*

---

## Scope-discipline rules (how to hit the fast end)

1. **Ship v0.1 rough at week 5** — static heuristics only; determinism is a selling point, so no LLM mode in v1.0.
2. **The site is a static generator**, not a web app — saves real time vs. a full web app.
3. **No auth, no accounts, no team tier** in v1.0.
4. **One transport at first** (stdio/local configs); remote HTTP deep-scan in v1.2.
5. **Protect the weekly build time** — block it as a recurring slot, or other priorities will eat it.
6. **Every rule needs all 4 artifacts** (rule, malicious fixture, benign fixture, test) — enforced by the `rule-authoring` skill; this is what prevents the credibility-killing FP spiral.

## Slippage risks (honest)

- **Limited weekly time budget** — plan for occasional dead weeks; build in buffer weeks per phase.
- **MCP SDK / client-config churn** — discovery parsers will need updating as clients ship changes; keep parser code data-driven.
- **FP crisis at site launch** — mitigated by the W16 spot-check gate; never auto-publish scores without the feedback loop.
- **Scope creep into dynamic analysis** — it's tempting (it's the coolest part) and it's a multi-week detour. It waits until v1.5.

## Success metrics

| Point | Target |
|---|---|
| v0.1 launch | 100 stars; 5 external issues/PRs |
| v1.0-beta | 500+ stars; 1,000+ servers scored; API serving |
| v1.0 launch | 2k+ stars; 10+ repos using the Action; 1 press citation |

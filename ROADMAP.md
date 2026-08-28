# mcpvet — v1 Timeline & Roadmap

*Effort assumption: ~5 hrs/week (20–25 hrs/month) alongside the services business. Times are calendar weeks, including ~1 dead week per month for services/busy periods.*

---

## What "v1.0 deployment" means (and doesn't)

**v1.0 is three things live:**
1. **CLI published** — PyPI/`uvx`, static scanning works, `--json` + SARIF output, `scan` + `inspect` commands.
2. **Reputation site + API live** — first batch of real public-registry MCP servers scanned, spot-checked, with per-server score pages and a rate-limited API.
3. **GitHub Action in the Marketplace** — enforces `mcp-policy.yaml` on PRs.

That's the minimum that earns press citations, team-tier waitlists, and the launch demo.

**Explicitly NOT in v1.0 (post-launch):** dynamic sandbox (egress logging, runtime rug-pull detection), LLM analysis mode, auth/accounts/team tier, remote HTTP server deep-scanning. These are v1.2–v2.0 differentiators, not launch requirements.

---

## Milestone timeline

| Milestone | Contents | Timeframe | Cumulative |
|---|---|---|---|
| **v0.1 — public CLI** | Config discovery (5 clients), rule engine, ~8 static rules, fixtures, pytest, PyPI/GitHub publish | 4–6 weeks | ~5 wks |
| v0.2 — hardening | FP passes vs top 50 real servers, docs/README, first Show HN / r/mcp post | +2–3 weeks | ~8 wks |
| **v1.0-beta — reputation site + API** | Registry poller, Postgres, FastAPI, static-generated score pages, badge, rate-limited API, ~1,000 servers scored & spot-checked | +6–8 weeks | ~15 wks |
| **v1.0 — enforcement + launch** | GitHub Action + `mcp-policy.yaml`, Marketplace listing, "State of MCP Security" report, press push | +3–4 weeks | ~18–20 wks |
| **v1.0 total** | | | **3.5–5 months** |
| v1.5 — dynamic sandbox | Docker sandbox runner, egress proxy, description-hash drift alerts | +6–8 weeks | ~6 months |

**Budget: ~120–160 real hours to v1.0.** AI-assisted coding makes writing fast (the CLI scaffold is a weekend with Claude Code); the time goes to MCP SDK edge cases, false-positive tuning, and site/infra glue.

**The big lever:** at 15–20 hrs/week (if services income stabilises and buys time), v1.0 compresses to **~8–10 weeks**. Keep 5 hrs/week until v0.1 ships, then decide.

---

## Week-by-week plan (each session has a defined "done")

### Phase 1 — v0.1 public CLI (Weeks 1–6)

- [x] **W1** — Repo init: copy scaffold, `pyproject.toml` (uv, typer, mcp SDK, pydantic, pytest, ruff), CLAUDE.md in place, CI green on empty tests. *Done: `uv run pytest` passes with 1 trivial test; repo public.*
- [x] **W2** — Config discovery: parsers for Claude Desktop/Code, Cursor, Windsurf, Gemini CLI paths; `inspect` command lists servers without executing. *Done: `mcpvet inspect` lists servers on your own machine; tests with sample configs.*
- [x] **W3** — Rule engine v1: YAML rule loader, findings dataclass, JSON output; first 4 static rules (hardcoded secrets in config, dangerous launch commands/curl-pipe-shell, over-broad filesystem/shell permissions, pinned-version check). *Done: each rule has the 4 artifacts (YAML + malicious fixture + benign fixture + test) per the `rule-authoring` skill.*
- [x] **W4** — Tool-description injection markers (`MCP-STATIC-005`: hidden HTML comments, zero-width chars, exfiltration-imperative phrasing), typosquat distance vs a bundled name list (`MCP-STATIC-006`, Levenshtein via rapidfuzz), package provenance (`MCP-STATIC-007`, npm-only, scoped to a missing `repository` field). *Done: 7 rules passing, not the originally-targeted 8 — provenance covers 1 of the 3 sub-checks named above; postinstall-script inspection and registry-age checks are still open. Provenance is network-dependent, so it's marked `network: true` and gated behind `mcpvet scan --deep`, off by default, per GOVERNANCE.md's separability rule. `--json` stays deterministic without `--deep`.*
- [ ] **W5** — SARIF output + `--fail-on` exit codes + README with install/quickstart: **done**, plus an `-o/--output` flag added so the README's documented command actually works. Publish to PyPI; tag v0.1: **not done** — `uv build` verified clean, but `git tag v0.1.0`, `git push --tags`, and `uv publish` are intentionally left for a human to run, per CLAUDE.md's publish-approval rule. *Done: `uvx mcpvet@0.1.0 scan <config>` works on a stranger's machine — blocked only on the tag/publish step above.*
- [ ] **W6** — Launch post: Show HN, r/mcp, r/cybersecurity, X/LinkedIn; dogfood on your own `.mcp.json`. *Done: 100 stars target; collect first 5 issues.*

### Phase 2 — v0.2 hardening (Weeks 7–9)

- [ ] **W7** — False-positive sweep: run against the 50 most-installed registry servers; tune severity/confidence; document every FP in CHANGELOG.
- [ ] **W8** — Docs site pass (usage, rule catalog with OWASP mappings, false-positive reporting flow); `mcpvet scan --self` dogfood command.
- [ ] **W9** — Buffer/week: bugfixes from launch feedback, first external PRs, community rules process (`GOVERNANCE.md`).

### Phase 3 — v1.0-beta reputation site + API (Weeks 10–17)

- [ ] **W10–11** — Registry poller: ingest official MCP Registry API nightly + dedupe; Postgres schema (servers, versions, scans, findings, hashes). *Done: cron job populates DB locally.*
- [ ] **W12–13** — Batch static scanning pipeline over all ingested servers; scoring engine (weighted 0–100, OWASP-coded findings). *Done: full registry scanned to JSON artifacts.*
- [ ] **W14** — **Static site generator** (not a web app): per-server score pages from nightly snapshots, leaderboard, typosquat cluster pages. Deploy cheap (Vercel/Cloudflare Pages). *Done: pages live for all scanned servers.*
- [ ] **W15** — FastAPI read-only API (`/v1/servers/{id}`, `/v1/check?name=`), rate-limited, free tier; embeddable badge for server authors.
- [ ] **W16** — **Manual spot-check sprint**: hand-verify scores on ~50 servers (credibility gate — a bad viral "it flagged a legit server" take costs more than delay). FP feedback button live.
- [ ] **W17** — Buffer/week: infra hardening, monitoring, cost check.

### Phase 4 — v1.0 enforcement + launch (Weeks 18–21)

- [ ] **W18** — `mcp-policy.yaml` spec (allowed servers, pinned versions/hashes, max permissions, blocked registries) + CLI `allowlist init/enforce`.
- [ ] **W19** — GitHub Action: on PR, diff MCP/agent config + skill dirs, post markdown risk report, fail on policy violation; Marketplace listing. *Done: action runs on a demo repo with green/red examples.*
- [ ] **W20** — **"State of MCP Security" report**: aggregate real numbers (% no-auth, % dangerous permissions, typosquat count, rug-pulls observed). Prepare pitches (Dark Reading, The Register, BleepingComputer, HN).
- [ ] **W21** — Launch: report + v1.0 tag + team-tier waitlist form. Notify every server author with a badge. *Done: v1.0 deployed; first press citation target hit.*

---

## Scope-discipline rules (how to hit the fast end)

1. **Ship v0.1 rough at week 5** — static heuristics only; determinism is a selling point, so no LLM mode in v1.0.
2. **The site is a static generator**, not a web app — saves ~2 weeks.
3. **No auth, no accounts, no team tier** in v1.0 — the waitlist is a form.
4. **One transport at first** (stdio/local configs); remote HTTP deep-scan in v1.2.
5. **Block the 5 hours as a recurring calendar event** — services income will eat this slot otherwise.
6. **Every rule needs all 4 artifacts** (rule, malicious fixture, benign fixture, test) — enforced by the `rule-authoring` skill; this is what prevents the credibility-killing FP spiral.

## Slippage risks (honest)

- **Services income priority** — plan ~1 dead week/month; v1.0 still lands inside 5 months.
- **MCP SDK / client-config churn** — discovery parsers will need updating as clients ship changes; keep parser code data-driven.
- **FP crisis at site launch** — mitigated by the W16 spot-check gate; never auto-publish scores without the feedback loop.
- **Scope creep into dynamic analysis** — it's tempting (it's the coolest part) and it's a 6–8 week detour. It waits until v1.5.

## Success metrics

| Point | Target |
|---|---|
| Week 6 | v0.1 public; 100 stars; 5 external issues/PRs |
| Week 17 (beta) | 500+ stars; 1,000+ servers scored; API serving |
| Week 21 (v1.0) | 2k+ stars; 10+ repos using the Action; 1 press citation; 5 team-tier waitlist conversations (2–3 from your defence/cyber network) |
| Month 6+ | First paid team or sovereign-pilot engagement |

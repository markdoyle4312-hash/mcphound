# Changelog

All notable changes to mcphound are documented here. Format loosely follows
[Keep a Changelog](https://keepachangelog.com/); this project doesn't use
SemVer strictly pre-1.0 (see ROADMAP.md).

## [Unreleased]

### W14 site now deploys nightly

`nightly-registry-scan` (`.github/workflows/nightly.yml`) is live: it polls
the registry, scans, exports to `site/data`, and deploys the Next.js site to
Vercel production on a daily cron. This needed a hosted Postgres for CI to
reach — `registry-poll`/`registry-scan` had only ever been run locally
before — so a Neon Postgres instance now backs it, schema migrated via
`alembic upgrade head`. Also fixed the job's `uv sync` missing
`--all-extras`, which would have failed the first real run since
`registry-poll` needs the `registry` extra.

## [0.1.3] — 2026-08-30

### CI fix: the entire pipeline had been running zero jobs

An internal audit (2026-08-30) found that `.github/workflows/ci.yml`'s
`nightly-registry-scan` job had a `schedule:` key nested under the job
instead of the workflow-level `on:` block — an invalid job key that fails
GitHub Actions' schema validation and causes the **whole workflow file** to
be rejected, not just that job. Effect: `test` (ruff + pytest), `self-scan`,
`docs-check`, `db-tests`, and `site-build` had never actually executed on
GitHub for any push or PR since the line was introduced (`1d3a6b4`) —
every "verified locally" claim in this changelog for the W14/W15 work below
was never confirmed by CI. Fixed by moving the cron trigger into its own
`nightly.yml` workflow so it can't invalidate the push/PR pipeline again.

### W15 FastAPI read-only API

New `src/mcphound/api/app.py`: a FastAPI app exposing three rate-limited
(slowapi) endpoints over the scored registry data — `GET /v1/servers/{slug}`
(full server detail + findings), `GET /v1/check?name=` (lookup by name), and
`GET /v1/badge/{slug}.svg` (embeddable SVG score badge, `api/badge.py`). The
two JSON endpoints are limited to 60/min, the badge to 300/min since it's
expected to be embedded in READMEs and hit far more often than a direct API
call. Response shapes are pydantic models in `api/schemas.py`; lookups go
through `api/queries.py` (server-by-name and server-by-slug). Badge/report
URLs are built from `MCPHOUND_SITE_BASE_URL` (defaults to
`https://mcphound.dev`, now documented in `.env.example`). DB test fixtures
were refactored (`tests/_db_fixtures.py`) so `tests/db`, `tests/registry`,
and the new `tests/api` share one setup, and the DB-migration skip logic
was fixed to only trigger for tests that actually touch the database.
Documented in `docs/api.md`.

### W14 static site + registry-export

New `mcphound registry-export --config config/registry.yaml --out DIR`
CLI command writes the scored-server artifacts (per-server JSON +
`index.json`) to a target directory for the site to consume, plus a
`typosquat-clusters.json` export (typosquat-neighbor logic refactored out
of the rule engine into shared `rules/typosquat.py`). `index.json` entries
gained a `slug` field for URL-safe per-server routing.

New `site/` — a Next.js app, statically exported (`next build`), reading
directly from the registry-export JSON with no server-side database access
of its own: a leaderboard home page (`/`), paginated full server listing
(`/browse/[page]`), per-server detail pages (`/servers/[...slug]`), and
typosquat watchlist pages (`/typosquats`, `/typosquats/[...slug]`). CI got
a `site-build` job (npm ci, vitest unit tests, `prepare:sample-data`,
`next build`) as a push/PR smoke test, plus a `nightly-registry-scan` job
(now in `nightly.yml`, still gated `if: false`) scaffolded to eventually
poll → scan → export → deploy to Vercel once the Vercel project and
secrets exist. Next was bumped to 16.3.3 and Vitest to 4.1.11, clearing 7
npm audit advisories.

### W12-13 batch scanning pipeline + scoring engine

New `mcphound registry-scan --config config/registry.yaml [--out DIR] [--dry-run]`
command: runs every in-scope (`is_latest=True`, not delisted) registry version
through the existing static rule engine, writes `scans`/`findings` rows,
computes a 0-100 score per server (multiplicative severity/confidence decay —
`registry/scoring.py`) into `server_scores`, and writes per-server JSON +
`index.json` (a leaderboard summary) to `artifacts/` for W14's static site
generator. Incremental: a version is skipped if it already has a scan from
the current mcphound version with no newer hash observed since. Unlike the
local `scan` command, network-dependent rules (npm provenance,
`MCP-STATIC-007`) always run here — a nightly batch job has no latency
pressure to hide behind `--deep`.

Ran the full pipeline against the live registry for the first time this
session, which surfaced two real bugs the code review alone hadn't caught:

- **`registry-poll` was pulling ~3.4x more than it needed.** `/v0.1/servers`
  returns one row per *published version* of every server unless filtered —
  ~85,000 rows for the registry's ~25,000 actually-current servers.
  `registry-scan` only ever reads `is_latest=True` versions, so the
  unfiltered walk was pure wasted paging + DB upserts. `client.py` now sends
  `version=latest` on every page request (confirmed against the live OpenAPI
  spec — also corrected `docs/registry-poller.md`'s stale claim that the
  registry has no delta mechanism at all; it exposes `updated_since`, just
  not wired up yet).
- **Case-colliding server names clobbered each other's artifact.** 5 pairs of
  real registry names differ only by case (e.g. `io.github.ClockNext/mcp` vs
  `io.github.Clocknext/mcp`). On a case-insensitive filesystem the second
  artifact write silently overwrote the first, while `index.json` still
  listed both as if each had its own file. `artifacts.py::_safe_filename`
  now appends a short deterministic hash suffix on a case-insensitive
  collision; servers are written in name order so which one gets the suffix
  is stable across runs.

Also added progress logging (`registry-poll` every 100 servers,
`registry-scan` every 25 versions) — both commands had no console feedback
otherwise, and a real run is a multi-minute-to-hour batch job.

**First full real-registry run** (2026-08-30, post-fix): 25,273 servers
scored, 821 flagged (score < 100), scores ranging 76-100, average 99.8.
Findings by rule: `MCP-STATIC-007` (no discoverable npm `repository` field)
817, `MCP-STATIC-003` (over-broad host/filesystem permissions) 2,
`MCP-STATIC-004` (unpinned/`@latest` package) 2 — the last is worth a closer
look later, since `registry/adapter.py` pins every npm/pypi version to its
exact release specifically to suppress this rule; these 2 likely have an
unpinned string inside `runtimeArguments`/`packageArguments` rather than the
main package identifier. Not yet spot-checked by a human (that's W16's
gate) — treat these as a first pass, not verified scores.

### W10-11 registry poller + Postgres schema

New `mcphound registry-poll --config config/registry.yaml [--dry-run]` command
ingests the official MCP Registry (`registry.modelcontextprotocol.io`) into a
local Postgres database. The API has no delta/webhook mechanism, so every run
pages the entire registry and upserts by natural key (idempotent — safe to run
repeatedly or interrupt). Servers/versions no longer present in a run are
soft-delisted (`delisted_at`, reversible), never hard-deleted — a taken-down
malicious server's history is exactly what mcphound's mission wants kept. A
new `hashes` table is an append-only ledger (only a new row when a version's
sha256 actually changes) — the foundation the v1.5 "description-hash drift
alerts" roadmap item needs. `scans`/`findings` tables are created but stay
empty until W12-13's batch scanning pipeline populates them.

New: SQLAlchemy 2.0 + Alembic under `src/mcphound/db/` (new optional
`registry` extra — kept out of the core install so `pip install mcphound`
stays lightweight for scanner-only use), `docker-compose.yml` for local
Postgres, a `db-tests` CI job running against a real Postgres service
container (not mocks — see `docs/registry-poller.md` for the schema rationale).
See `docs/registry-poller.md` for local setup and nightly-scheduling docs
(cron/Task Scheduler — no custom scheduling logic was built).

### W9 community rules process

GOVERNANCE.md's "Contributing rules" section was three bullet points marked
"working notes — expand before v0.1 launch." Expanded it into an actual process:
how to propose a rule (issue first, using a new template), the non-negotiable
4-artifact PR bar, what a review actually checks (OWASP mapping, a genuinely
close-call benign fixture, no new false positives against the `tests/fp_sweep/`
real-world corpus, network calls marked+gated, no duplicate coverage, justified
severity/confidence), and a plain "best-effort, no SLA" turnaround note since
this is solo-maintained. Added `.github/PULL_REQUEST_TEMPLATE.md` (checklist
mirrors the process doc) and `.github/ISSUE_TEMPLATE/new-rule-proposal.md`.

The other half of W9's roadmap line — "bugfixes from launch feedback, first
external PRs" — doesn't apply yet: W6 (the actual launch post) hasn't happened,
so there's no real feedback or external PRs to act on. Left that part of the
roadmap line unstruck rather than fabricating activity that hasn't occurred.

### W8 docs pass + dogfood command

- **`docs/rules.md`** — a generated rule catalog (ID, title, severity, confidence,
  OWASP mapping, detection summary, recommendation, references) built by
  `scripts/generate_rule_docs.py` from `src/mcphound/rules/*.yaml`. Never hand-edit
  it — it can't drift from the actual rules because it isn't hand-maintained. `make
  docs` regenerates it; a new `docs-check` CI job fails the build if it's stale.
- **`mcphound scan --self`** — scans only this project's own configs (`.mcp.json`,
  `opencode.json`/`opencode.jsonc` in the current directory), skipping user-level
  client configs. Replaces the hardcoded-filename dogfood pattern in the Makefile
  and CI's `self-scan` job; the now-fully-superseded `scripts/self-scan.sh`
  (a pre-mcphound W1 fallback) is deleted.
- **`mcphound feedback <rule-id> [--note TEXT]`** — prints a pre-filled GitHub
  "new issue" URL for reporting a false positive (rule ID/title, mcphound version,
  a redaction reminder). No network call, no auth. Implements the flow
  GOVERNANCE.md's "False positives" section had marked "to be built."

### Fixed

- `src/mcphound/__init__.py`'s `__version__` was hardcoded `"0.1.0"` while the
  package had already shipped `0.1.2` — it now reads from installed package
  metadata (`importlib.metadata.version`), so it can't drift from `pyproject.toml`
  again.
- `rules/loader.py` and `discovery/clients.py` read YAML/config files with
  `Path.read_text()` (no explicit encoding), which decoded non-ASCII characters
  (e.g. em dashes in rule `description`/`detail` text) using the platform default
  encoding — mojibake on Windows, where that default isn't UTF-8. Both now force
  `encoding="utf-8"`. Found while generating `docs/rules.md`, whose output was
  visibly corrupted before this fix.

### W7 false-positive sweep

Ran `mcphound scan --deep` against a corpus of 36 real, source-verified MCP server
configs (`tests/fp_sweep/registry_top50.json` — official reference implementations plus
widely-used vendor and community servers; see `tests/fp_sweep/SOURCES.md` for the exact
sources and the honesty note on why it's 36, not the roadmap's nominal 50: every
candidate whose real launch command couldn't be confirmed against a primary source was
dropped rather than guessed).

**Result: zero false positives.** `MCP-STATIC-001` (hardcoded secrets), `-002` (curl \|
sh), `-003` (over-broad permissions), `-005` (injection markers), and `-006`
(typosquat) did not fire on any of the 36 servers, including several with
realistic-looking placeholder tokens in `env` (`ntn_****`, `xoxp-[your-token]`,
`pat123.abc123`) — confirming the secret-shape regex doesn't over-match plausible
placeholders.

`MCP-STATIC-004` (unpinned/`@latest` version) and `MCP-STATIC-007` (npm provenance,
`--deep` only) both fired, and both were true positives on inspection:

- **`MCP-STATIC-004` fired on 31/36 servers (86%).** This is not a rule bug — it's how
  most vendors actually document their `npx`/`uvx` install command (no version pin).
  Severity stays at `medium`: prevalence in the wild doesn't reduce the actual
  rug-pull/registry-mutation risk of an unpinned package, so the finding isn't softened.
  Documented here instead, as the calibration data a user of `--fail-on medium` should
  expect.
- **`MCP-STATIC-007` fired on `brave-search`, `puppeteer`, and `google-maps`** — all
  three now-archived official reference servers, confirmed against the live npm
  registry to genuinely have no `repository` field in their published metadata. Real
  signal, not a scanner bug.

The sweep also surfaced a genuine **detection gap** (false negative) in `MCP-STATIC-004`:
its regex only recognized bare `npx`/`uvx <pkg>` invocations, missing `uvx --from
<pkg>@latest ...` (the `redis` server's real launch command) and `uv run --with <pkg>
...` (the `mcp-clickhouse` server's), both of which are genuinely unpinned. Fixed by
extending the rule's regex to also accept `--from`/`--with` flags and a leading `uv run`
form; new malicious/benign fixture pairs added for both shapes
(`tests/fixtures/static/MCP-STATIC-004/`).

Added `tests/fp_sweep/test_fp_sweep.py` as a permanent regression guard: it re-scans the
corpus and fails CI if any rule other than `-004`/`-007` fires (a new false positive) or
if `-007`'s three known hits change (a detection regression or an npm metadata change
worth re-verifying).

## [0.1.2] — 2026-08-29

### Changed
- Finished the `mcpvet`/`mcp-vet` → `mcphound` rename across docs, configs,
  and test fixtures. Removed the `mcpvet` back-compat CLI alias — `mcphound`
  is the only entry point now. Renamed the fixture canary marker to
  `MCPHOUND-FIXTURE-CANARY` and the example DB env vars to
  `MCPHOUND_DATABASE_URL_RO`.

## [0.1.1] — 2026-08-29

### Fixed
- `scan`/`inspect` silently ignored an explicitly-passed config file that
  didn't exist, exiting 0 as if nothing were wrong. They now print a
  warning to stderr and exit 1 when an explicit path is missing.
  Auto-discovery finding no configs is unchanged — that's an expected,
  silent (exit 0) outcome, not an error.

## [0.1.0] — 2026-08-29

First public release. Static-only scanning; nothing here ever executes an
MCP server.

### What v0.1 does

mcphound discovers the MCP servers configured in your AI coding clients
(Claude Desktop/Code, Cursor, Windsurf, Gemini CLI, OpenCode — both `.json`
and JSON5-style `.jsonc`) and runs a set of static detection rules against
each server's launch command, environment, and (optionally) npm registry
metadata. Every finding maps to an OWASP LLM Top 10 or Agentic/MCP Top 10
code. Output is human-readable by default, or `--json` / `--sarif` for
tooling and GitHub code scanning, with `--fail-on` exit codes for CI.

Install and run (published on PyPI as `mcphound`):

```bash
uvx mcphound scan
```

### Detection rules

| ID | Title | Severity | OWASP |
|---|---|---|---|
| `MCP-STATIC-001` | Hardcoded secret in MCP server environment | high | LLM02 |
| `MCP-STATIC-002` | Remote code download-and-execute in launch command (curl/wget \| sh) | critical | AST04 |
| `MCP-STATIC-003` | Over-broad host/filesystem permissions in launch command | high | LLM08 |
| `MCP-STATIC-004` | Unpinned or `@latest` package version in launch command | medium | AST04 |
| `MCP-STATIC-005` | Tool-description injection markers (hidden HTML comments, zero-width Unicode, exfiltration-imperative phrasing) | critical | LLM01 |
| `MCP-STATIC-006` | Typosquat of a known MCP server package name (Levenshtein distance) | high | AST04 |
| `MCP-STATIC-007` | npm package has no discoverable source repository — network-dependent, opt-in via `--deep` | medium | AST04 |

Every rule ships with all four required artifacts: the YAML rule, a
malicious fixture, a benign fixture (false-positive guard), and a pytest.

### Not yet (post-v0.1)

- **Dynamic analysis** — Docker sandbox runner, egress-proxy network,
  runtime rug-pull / description-drift detection. Planned for v1.5
  (ROADMAP.md).
- **Reputation site + API** — registry poller, per-server score pages,
  leaderboard, rate-limited API. Planned for v1.0-beta.
- **GitHub Action** — `mcp-policy.yaml` allowlist enforcement on PRs.
  Planned for v1.0.

### Added
- Config discovery for Claude Desktop/Code, Cursor, Windsurf, Gemini CLI,
  and OpenCode (`.json` and `.jsonc`, including trailing-comma JSON5 style).
- `mcphound inspect` — lists configured servers without executing them.
- `mcphound scan` — runs detection rules; `--json`, `--sarif`, `--fail-on`,
  `-o/--output`, and `--deep` (opt-in network-dependent checks).
- SARIF 2.1.0 output for GitHub code scanning.
- Seven static detection rules — see table above.

### Fixed
- `_target_text`'s raw-JSON dump used `ensure_ascii=True`, silently hex-escaping
  zero-width Unicode characters before MCP-STATIC-005 could see them.
- `.jsonc` configs with a trailing comma before `}`/`]` (valid JSON5, common
  in hand-edited `opencode.jsonc`) failed to parse; the repo's own
  `opencode.jsonc` hit this.
- SARIF `informationUri` pointed at a placeholder org/repo instead of the
  real repository.
- SARIF `artifactLocation.uri` was a Windows-style path with a non-URI
  `" :: server"` suffix appended, which is not a valid URI.
- SARIF `security-severity` was set to the severity word (`"high"`,
  `"critical"`) instead of a numeric CVSS-like score; GitHub's code-scanning
  ingestion rejects non-numeric values outright, so every SARIF upload would
  have silently failed until this fix. Verified with a live upload to
  GitHub's code-scanning API during release prep.

### Known limitations
- Package provenance (`MCP-STATIC-007`) only checks for a missing npm
  `repository` field. Postinstall-script inspection and registry-age checks
  (both named in ROADMAP.md's W4) are not implemented yet.
- The typosquat reference list (`src/mcphound/rules/data/known_servers.yaml`)
  is a small hand-curated seed, not the official registry — Phase 2's
  registry poller will supersede it.
- PyPI packages (`uvx`-launched) aren't covered by MCP-STATIC-007 yet, only
  npm/`npx`.

### Dogfood / canary results
- `mcphound scan .mcp.json opencode.jsonc --fail-on high`: zero findings against
  this repo's own agent configs.
- `mcphound scan --deep` against 5 well-known real MCP packages
  (`@modelcontextprotocol/server-filesystem`, `-postgres`, `-everything`,
  `@upstash/context7-mcp`, `@playwright/mcp`): one genuine finding —
  `@modelcontextprotocol/server-postgres` has no `repository` field in its
  npm metadata (confirmed against the live registry; the package is also
  marked deprecated on npm, unrelated to this rule but worth knowing).
  No previous release to diff against — this is the baseline.

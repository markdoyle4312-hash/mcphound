# Registry poller

`mcphound registry-poll` ingests the official MCP Registry
(https://registry.modelcontextprotocol.io) into a local Postgres database:
servers, their published versions/packages/remotes, and a hash-change ledger
per version. It's idempotent — running it repeatedly upserts by natural key
and never creates duplicate rows.

## Local setup

1. `docker compose up -d db` — starts Postgres 16 in a container (`make db-up`).
2. Set `MCPHOUND_DATABASE_URL` (see `.env.example`):
   ```bash
   export MCPHOUND_DATABASE_URL=postgresql+psycopg://mcphound:mcphound@localhost:5432/mcphound_dev
   ```
3. `uv sync --all-extras` — installs the `registry` extra (SQLAlchemy, Alembic, psycopg).
4. `uv run alembic upgrade head` (`make db-migrate`) — creates the schema.
5. `uv run mcphound registry-poll --config config/registry.yaml --dry-run` — preview
   without writing.
6. `uv run mcphound registry-poll --config config/registry.yaml` (`make registry-poll`) —
   real run.

## Running it nightly

There's no built-in scheduler — this is a plain CLI command. In production,
`.github/workflows/nightly.yml`'s `nightly-registry-scan` job runs it on a
daily cron against a hosted Neon Postgres instance (`MCPHOUND_DATABASE_URL`
repo secret), then exports and deploys the site to Cloudflare Pages. For local/manual
scheduling instead, use whatever mechanism your OS already has:

**Unix (cron):** add a line to `crontab -e` (adjust the path and DSN):

```
0 4 * * * cd /path/to/mcphound && MCPHOUND_DATABASE_URL=postgresql+psycopg://mcphound:mcphound@localhost:5432/mcphound_dev uv run mcphound registry-poll --config config/registry.yaml >> registry-poll.log 2>&1
```

**Windows (Task Scheduler):** create a basic task that runs daily, with:
- Program: `uv`
- Arguments: `run mcphound registry-poll --config config/registry.yaml`
- Start in: the repo root
- "Add an argument" won't let you set an env var — instead wrap the command in
  a `.ps1` script that sets `$env:MCPHOUND_DATABASE_URL` first and point the
  task at that script.

## Scanning: `mcphound registry-scan`

Once the poller has populated `servers`/`versions`/`hashes`, `registry-scan`
batch-runs the existing static rule engine against every currently-listed
("latest", not delisted) version, writes `scans`/`findings` rows, computes a
0-100 score per server into `server_scores`, and writes JSON artifacts for
the future static site generator:

```bash
uv run mcphound registry-scan --config config/registry.yaml
# or: make registry-scan
```

It's incremental: a version is skipped if it already has a scan from the
current mcphound version and no newer hash has been observed since — so a
nightly cron just chains the two commands:

```
registry-poll && registry-scan
```

`--dry-run` runs the full pipeline but rolls back instead of committing, and
skips writing artifacts (there's nothing committed to publish). `--out`
overrides the output directory (default: `artifacts_dir` in
`config/registry.yaml`, itself defaulting to `./artifacts`) — writes
`artifacts/servers/<name>.json` per server plus `artifacts/index.json` as a
leaderboard summary.

Network-dependent rules (currently just the npm provenance check,
`MCP-STATIC-007`) always run here, unlike the local `scan` command's
`--deep` gate — a nightly batch job has no latency pressure, and provenance
checking against the public registry is exactly what this pipeline exists
to produce.

Rule evaluation runs on a thread pool (`--workers`, default 16) since it's
I/O-bound — mostly that same npm provenance HTTP call, one per in-scope
version. `--workers 1` reproduces the old fully-sequential behavior.

## Site export: `mcphound registry-export`

`registry-scan` already writes JSON artifacts as part of its pipeline, but
re-running a full scan just to refresh those files is wasteful when scores
haven't changed. `registry-export` re-materializes the same artifacts
(`index.json`, `servers/<name>.json`, `typosquat-clusters.json`,
`newly-flagged.json`) directly from already-scored DB state — no
rescanning, no DB writes:

```bash
uv run mcphound registry-export --config config/registry.yaml
# or with an explicit output directory:
uv run mcphound registry-export --out site/data
```

This is what the W14 static site's build pipeline runs before `next build`
— see `site/README.md`. `index.json` entries also carry a `slug` field (the
exact filename, minus `.json`, of that server's file under
`artifacts/servers/`) so the site never has to reimplement the
escaping/collision logic that produces those filenames.

`typosquat-clusters.json` holds, for each name in `MCP-STATIC-006`'s bundled
reference list (`src/mcphound/rules/data/known_servers.yaml`), every
currently-listed registry package within that rule's edit-distance
threshold (excluding an exact match) — an empty `neighbors` list is
expected and valid, not a bug, until the registry actually has a lookalike
or the reference list grows.

`newly-flagged.json` holds every server whose most recent `ServerScore` row
is below 100 while the one immediately before it (if any) was 100 or the
server had no prior score — i.e. servers that just crossed into flagged
status on the latest run, not a rolling history of everything currently
flagged. It's what the site's `/feed.xml` and `/feed.json` are built from
(`write_newly_flagged()` in `registry/artifacts.py`); because it only ever
compares the latest run to the one before it, a feed reader polling less
often than the nightly cron could miss a server that crosses below 100 and
back above it between two polls.

## Schema

Six tables (`src/mcphound/db/models.py`), all timestamps `timestamptz`, every
table with a surrogate bigserial `id` plus `created_at`/`updated_at` bookkeeping.

**`servers`** — one row per registry entity, keyed on `name` (the registry's
reverse-DNS id, e.g. `io.github.foo/bar-server`). Carries `title`,
`description`, `website_url`, `repository_url`/`repository_source`, and a
`raw_json` copy of the full server-level entry for forward-compat. `first_seen_at`
is set once; `last_seen_at` is stamped on every run the server still appears in.

**`versions`** — one row per **launchable artifact**: server × version ×
(package-or-remote). A server publishing both an npm package and a hosted
remote for the same version string gets two rows — this grain matches what a
future scan would actually check (one row = one thing that could be launched
and inspected), not the registry's own per-server-version grouping. Unique key:
`(server_id, version, registry_type, identifier)`. `registry_type` is
`npm`/`pypi`/`cargo`/`oci`/`nuget`/`mcpb`/`remote`; `identifier` is the package
name, or the remote URL when `registry_type='remote'`. `runtime_arguments`,
`package_arguments`, `environment_variables` are stored as raw `jsonb` — W12-13's
scanning pipeline needs these to reconstruct a launch command, not a
lossy-flattened version.

**`hashes`** — an **append-only observation log**, not a 1:1 mirror of the
registry's `fileSha256`. The poller only inserts a row when a version's hash
differs from the last one on file for that version (`_maybe_insert_hash` in
`src/mcphound/registry/poller.py`). This is deliberate: it's the ledger the
v1.5 roadmap item ("description-hash drift alerts") needs — the same version
string suddenly resolving to a different hash than last observed is a rug-pull
signal. Nothing consumes that signal yet, but the data has to start
accumulating now to be useful later. Indexed on `(version_id, observed_at)`
for "latest hash for this version" reads.

**`scans` / `findings`** — created here, populated by `registry-scan` (see
above), not this poller. `scans` holds `version_id`, `scanned_at`,
`mcphound_version`, `deep`, `status`; `findings` mirrors every field on
`mcphound.models.Finding` (`rule_id`, `title`, `severity`, `confidence`,
`owasp`, `phase`, `detail`, `recommendation`) so DB rows and CLI JSON output
never diverge in shape.

**`server_scores`** — one append-only row per scoring run
(`server_id`, `computed_at`, `score`, `finding_count`, `mcphound_version`),
mirroring the `hashes` ledger style so a server's score history is queryable
without recomputing it. Populated by `registry-scan`'s scoring pass.

Despite the column name, `mcphound_version` on both tables holds a rule-set
content fingerprint (`rules_fingerprint()` in `rules/loader.py`, e.g.
`rules-8f19a2c3d4e5f601`), not the literal `mcphound.__version__` string. The
scan pipeline uses it as the incremental-rescan staleness key, and keying it
to the package version instead forced a full ~25k-version rescan on every
release regardless of whether detection logic actually changed — including
docs/CI/packaging-only releases, which this project ships several of a day
pre-1.0. See the docstring on `rules_fingerprint()` for the full reasoning.

**Delisting is soft, not a `DELETE`.** Each run stamps `last_seen_at` on
everything it touches, then mark-and-sweeps: anything with `last_seen_at`
older than the run's start gets `delisted_at` set (and cleared again if it
reappears in a later run). A taken-down malicious server's history is exactly
what mcphound's mission wants kept — a hard delete would erase the evidence.

**Why a full re-page every run, not a delta fetch:** the registry API
(`GET /v0.1/servers`, cursor-paginated via `cursor`/`limit` and
`metadata.nextCursor`) has no webhook mechanism — a poller has no cheaper
option than walking the whole (filtered) listing each run and diffing
locally against `last_seen_at`. Upserts use Postgres `INSERT ... ON CONFLICT
DO UPDATE`, so this scales with registry size rather than requiring an
in-memory diff against the whole existing table.

**`version=latest` filter (added 2026-08-30):** without it, `/v0.1/servers`
returns one row per *published version* of every server — for the live
registry that's roughly 85,000 rows for ~25,000 actually-current servers,
since old superseded versions stay listed. `registry-scan` only ever reads
`is_latest=True` rows (`scanner.py::_in_scope_versions`), so the un-filtered
~3x volume was pure waste on every run — more HTTP page-fetches, more DB
upserts, no additional coverage. `client.py::_fetch_page` now always sends
`version=latest`. One consequence: mcphound no longer bulk-ingests
already-superseded version rows on each poll; it still accumulates each
server's version history over time naturally (a new "latest" lands as a new
row on the run after it's published), just not the full backlog on day one.

The API also exposes `updated_since` (an RFC3339 delta filter) per its
OpenAPI spec, which the original "no delta mechanism" note above was wrong
about — the poller doesn't use it yet. That's a separate future optimization
(swapping the full walk for an incremental one), not part of this fix.

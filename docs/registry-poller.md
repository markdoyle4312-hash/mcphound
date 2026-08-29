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

There's no built-in scheduler — this is a plain CLI command, so use whatever
scheduling mechanism your OS already has. `.github/workflows/ci.yml` has a
`nightly-registry-scan` job stub for this, but it's disabled (`if: false`)
until there's a hosted database and secrets to run it against; for now, run
it locally or on a machine you control.

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

## Schema

See `docs/superpowers/specs/2026-08-29-registry-poller-design.md` for the full
column-level schema and the reasoning behind it (why `hashes` is append-only,
why `versions` is keyed the way it is, why delisting is soft).

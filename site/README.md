# mcphound site

The W14 static site: per-server score pages, a flagged-servers leaderboard,
a paginated full listing, and typosquat watchlist pages. Built with
Next.js (App Router, static export) and Tailwind CSS.

## Local development

The site reads JSON from `data/` (gitignored — never commit real data).

For real data, from the repo root (requires `MCPHOUND_DATABASE_URL` set and
at least one `registry-scan` run — see `docs/registry-poller.md`):

```bash
uv run mcphound registry-export --config config/registry.yaml --out site/data
```

For quick UI iteration without a database, use the committed sample
fixtures instead:

```bash
npm run prepare:sample-data
```

Then:

```bash
npm install
npm run dev      # http://localhost:3000
npm test         # vitest unit tests (lib/ only — pages are covered by `npm run build`)
npm run lint     # eslint (flat config, eslint-config-next — next lint was removed in Next 16)
npm run build    # static export to out/
```

## Deployment

This site deploys to Vercel via the Vercel CLI from the nightly CI job
(`nightly-registry-scan` in `.github/workflows/nightly.yml`), not via a
git-triggered Vercel build — the export step needs live Postgres access,
which only the CI runner has, and `data/` is never committed.

The project is linked (Vercel project `marksit/site`) and the CI job runs
daily (`0 18 * * *` UTC): poll the registry → scan → export to `site/data`
→ `npm ci` → build and deploy to Vercel production, all against a hosted
Neon Postgres instance (`MCPHOUND_DATABASE_URL` repo secret). Repo secrets
in use: `VERCEL_TOKEN`, `VERCEL_ORG_ID`, `VERCEL_PROJECT_ID`,
`MCPHOUND_DATABASE_URL`.

The `site-build` CI job (against sample data, on every push/PR) is a
separate, faster smoke test — it doesn't deploy anything.

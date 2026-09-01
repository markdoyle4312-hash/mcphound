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

This site deploys to Cloudflare Pages via `wrangler pages deploy` from the
nightly CI job (`nightly-registry-scan` in `.github/workflows/nightly.yml`),
not via a git-triggered build — the export step needs live Postgres access,
which only the CI runner has, and `data/` is never committed.

It moved off Vercel because `output: "export"` plus `generateStaticParams()`
over the full registry index produced one route per scanned server
(~28k+ at current registry size), which blew well past Vercel's
2,048-routes-per-deployment cap. Cloudflare Pages turned out to have its
own cap — 20,000 files on the Free plan (100,000 on paid plans) — which the
same one-page-per-server approach hit within days. Server detail pages
(`/servers/<name>`) are now a single static Client Component shell that
fetches its data from one of 64 fixed-count JSON shards under
`public/data/` (built by the `prebuild` npm script,
`scripts/build-server-shards.ts`) at runtime, keyed by server name — so
deployed file count no longer scales with registry size. A
`public/_redirects` rule (`/servers/* /servers 200`) keeps `/servers/<name>`
URLs resolving to that shell. `/browse/**` and `/typosquats/**` are
unaffected — both stay small enough to prerender normally.

The Cloudflare Pages project (`mcphound`) was created once via the
dashboard/`wrangler pages project create` — the nightly job only ever
deploys to it, it doesn't create it. The CI job runs daily (`0 18 * * *`
UTC): poll the registry → scan → export to `site/data` → `npm ci` →
`npm run build` (static export to `out/`) → `wrangler pages deploy`, all
against a hosted Neon Postgres instance (`MCPHOUND_DATABASE_URL` repo
secret). Repo secrets in use: `CLOUDFLARE_API_TOKEN`,
`CLOUDFLARE_ACCOUNT_ID`, `MCPHOUND_DATABASE_URL`.

The `site-build` CI job (against sample data, on every push/PR) is a
separate, faster smoke test — it doesn't deploy anything.

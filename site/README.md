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

## Deployment (one-time manual setup)

This site deploys to Vercel via the Vercel CLI from the nightly CI job
(`nightly-registry-scan` in `.github/workflows/ci.yml`), not via a
git-triggered Vercel build — the export step needs live Postgres access,
which only the CI runner has, and `data/` is never committed.

1. Create a Vercel account/project (`vercel.com`), pointed at this repo
   with **Root Directory** set to `site/` — or run `npx vercel link` from
   `site/` locally and follow the prompts.
2. Generate a Vercel access token (Vercel dashboard → Settings → Tokens).
3. After linking, `site/.vercel/project.json` has your `orgId`/`projectId`.
4. Add three repo secrets (GitHub → Settings → Secrets → Actions):
   `VERCEL_TOKEN`, `VERCEL_ORG_ID`, `VERCEL_PROJECT_ID`.
5. Flip `nightly-registry-scan`'s `if: false` to `if: true` (or a real
   schedule condition) in `.github/workflows/ci.yml`.

Until this is done, the site only builds in CI (the `site-build` job,
against sample data) — nothing is deployed automatically.

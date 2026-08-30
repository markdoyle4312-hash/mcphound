# API

A free, read-only, rate-limited API over mcphound's registry-scan results.
No auth, no accounts — this is the public-surface API described in
`ROADMAP.md` W15.

## Running it locally

    uv sync --extra registry --extra api
    export MCPHOUND_DATABASE_URL=postgresql+psycopg://mcphound:mcphound@localhost:5432/mcphound_dev
    uv run uvicorn mcphound.api.app:app --reload

See `docs/registry-poller.md` for getting a populated local Postgres database
(the API has nothing to show against an empty one).

## Endpoints

### `GET /v1/servers/{slug}`

Full score + findings for one server, keyed by the same slug used in the
site's `/servers/{slug}` URLs (see `artifacts/index.json`'s `slug` field, or
derive it yourself: replace `/` with `__`, then anything outside
`[A-Za-z0-9_.@-]` with `_`). 404 if the server hasn't been scored yet.

Rate limit: 60/minute per IP.

```json
{
  "name": "io.github.acme/tool",
  "slug": "io.github.acme__tool",
  "score": 65,
  "finding_count": 1,
  "last_scanned_at": "2026-08-30T04:00:00+00:00",
  "findings": [
    {
      "rule_id": "MCP-STATIC-001",
      "title": "Hardcoded secret in launch config",
      "severity": "high",
      "confidence": "high",
      "owasp": "LLM07",
      "detail": "...",
      "recommendation": "..."
    }
  ]
}
```

### `GET /v1/check?name=<raw-registry-name>`

A programmatic "does this look safe" probe, keyed by the registry's raw
server name (not the slug) — the thing a server author or a CI policy check
already knows. Always returns 200; `found: false` for anything not yet
scanned, so callers don't need exception handling for the common case.

Rate limit: 60/minute per IP.

```json
{"found": true, "name": "io.github.acme/tool", "slug": "io.github.acme__tool", "score": 65, "finding_count": 1, "report_url": "https://mcphound.dev/servers/io.github.acme__tool"}
```

### `GET /v1/badge/{slug}.svg`

An embeddable SVG badge, colored green (score >= 90), yellow (70-89), or red
(< 70). 404 (not a fallback "unknown" badge) for an unscored slug, so a typo
doesn't silently render as if it were a real score. Cached for an hour
(`Cache-Control: public, max-age=3600`) — safe to embed in a README without
worrying about load.

Rate limit: 300/minute per IP (higher than the JSON endpoints, since badges
are meant to be hit often).

Markdown snippet for server authors:

    [![mcphound score](https://mcphound.dev/v1/badge/io.github.acme__tool.svg)](https://mcphound.dev/servers/io.github.acme__tool)

(Replace `io.github.acme__tool` with your own server's slug, and
`mcphound.dev` with wherever this API ends up actually hosted — see
`MCPHOUND_SITE_BASE_URL` / the deploy target `mcphound.api.app:app`.)

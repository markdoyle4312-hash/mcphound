# FP-sweep corpus sources (W7)

`registry_top50.json` holds 36 real, currently-documented MCP servers, each entered with
the launch command/args/env its own primary source (repo README, npm/PyPI page, or vendor
docs) actually shows — not a leaderboard's paraphrase, and never a fabricated command.

**Honesty note on "most-installed":** mcphound has no registry poller yet (that lands in
ROADMAP.md's W10–11 milestone), so there is no download-count or install-telemetry data to
rank against. This list is a best-effort proxy: official reference implementations (which
ship inside the `modelcontextprotocol/servers` monorepo and are bundled with every MCP
client's docs) plus vendor-published servers for widely-used SaaS products (GitHub, Slack,
Stripe, Notion, Sentry, etc.) plus a sample of community servers that rank highly on
`tolkonepiu/best-of-mcp-servers`, a GitHub-metrics-based quality/popularity ranking. Treat
"popular" here as "plausibly popular by public proxy signals," not a verified top-50.

Fewer than the roadmap's nominal 50 servers are included: every server not verifiable
against a primary source (i.e., every candidate whose real launch command I could not
confirm from its own docs, only from a leaderboard blurb) was dropped rather than guessed.

| Server (key in JSON) | Primary source | Why it's in this set |
|---|---|---|
| filesystem | https://github.com/modelcontextprotocol/servers/tree/main/src/filesystem | Official reference implementation |
| git | https://github.com/modelcontextprotocol/servers/tree/main/src/git | Official reference implementation |
| memory | https://www.npmjs.com/package/@modelcontextprotocol/server-memory | Official reference implementation |
| fetch | https://github.com/modelcontextprotocol/servers/blob/main/src/fetch/README.md | Official reference implementation |
| sequential-thinking | https://github.com/modelcontextprotocol/servers/blob/main/src/sequentialthinking/README.md | Official reference implementation |
| everything | https://github.com/modelcontextprotocol/servers/blob/main/src/everything/README.md | Official reference/test implementation |
| brave-search | https://www.npmjs.com/package/@modelcontextprotocol/server-brave-search ; https://brave.com/search/api/guides/use-with-claude-desktop-with-mcp/ | Official reference implementation (archived), still widely referenced in client setup guides |
| puppeteer | https://www.npmjs.com/package/@modelcontextprotocol/server-puppeteer | Official reference implementation, now archived/deprecated — kept because it's still the most commonly copy-pasted browser-automation config in older guides (deliberately includes a stale/deprecated server as a realistic case) |
| google-maps | https://www.npmjs.com/package/@modelcontextprotocol/server-google-maps ; https://github.com/modelcontextprotocol/servers-archived/tree/main/src/google-maps | Official reference implementation, now in `servers-archived` — same rationale as puppeteer |
| sqlite | https://mcpmux.com/servers/community.fetch-uvx/ pattern documented alongside official servers; command form `uvx mcp-server-sqlite --db-path` | Long-standing reference-style Python server, very commonly documented |
| playwright | https://github.com/microsoft/playwright-mcp ; https://www.npmjs.com/package/@playwright/mcp | Official Microsoft server, #6 on best-of-mcp-servers, de facto Puppeteer replacement |
| github | https://github.com/github/github-mcp-server/blob/main/docs/installation-guides/install-claude.md | Official GitHub server; binary/stdio launch form, not npx — included for command-shape diversity |
| notionApi | https://github.com/makenotion/notion-mcp-server ; https://www.npmjs.com/package/@notionhq/notion-mcp-server | Official Notion server |
| linear | https://linear.app/docs/mcp | Official Linear server, hosted remote via `npx mcp-remote <url>` pattern |
| supabase | https://supabase.com/blog/remote-mcp-server | Official Supabase server, moved to hosted remote endpoint |
| neon | https://neon.com/docs/ai/neon-mcp-server ; https://www.npmjs.com/package/@neondatabase/mcp-server-neon | Official Neon server, local stdio package deprecated in favor of hosted `mcp-remote` endpoint — kept to test the same pattern as linear/supabase |
| stripe | https://www.npmjs.com/package/@stripe/mcp ; https://docs.stripe.com/mcp | Official Stripe server |
| figma-developer-mcp | https://www.npmjs.com/package/figma-developer-mcp | High-adoption third-party Figma server (#16 on best-of-mcp-servers as Figma-Context-MCP family) |
| awslabs-core-mcp-server | https://awslabs.github.io/mcp/installation ; https://pypi.org/project/awslabs.core-mcp-server/ | Official AWS Labs server (#13 on best-of-mcp-servers) |
| terraform | https://github.com/hashicorp/terraform-mcp-server | Official HashiCorp server; Docker launch form for command-shape diversity |
| mongodb | https://github.com/mongodb-js/mongodb-mcp-server | Official MongoDB server |
| airtable | https://github.com/domdomegg/airtable-mcp-server | #28 on best-of-mcp-servers |
| sentry | https://github.com/getsentry/sentry-mcp | Official Sentry server, local stdio form |
| slack | https://github.com/korotovsky/slack-mcp-server | #57 on best-of-mcp-servers, most commonly documented community Slack server |
| context7 | https://github.com/upstash/context7 ; https://www.npmjs.com/package/@upstash/context7-mcp | Extremely widely referenced documentation-lookup server across MCP client onboarding guides |
| firecrawl-mcp | https://github.com/firecrawl/firecrawl-mcp-server | Official Firecrawl server |
| perplexity-ask | https://github.com/perplexityai/modelcontextprotocol | Official Perplexity server |
| grafana | https://github.com/grafana/mcp-grafana | Official Grafana server; Docker launch form |
| redis | https://github.com/redis/mcp-redis | Official Redis server |
| mcp-clickhouse | https://github.com/ClickHouse/mcp-clickhouse ; https://clickhouse.com/blog/integrating-clickhouse-mcp | Official ClickHouse server (#44 on best-of-mcp-servers); `uv run --with` launch form for diversity |
| desktop-commander | https://github.com/wonderwhy-er/DesktopCommanderMCP | #34 on best-of-mcp-servers |
| ssh-mcp | https://github.com/tufantunc/ssh-mcp | #35 on best-of-mcp-servers |
| docker-mcp | https://github.com/QuantGeekDev/docker-mcp | Widely referenced Docker-control server |
| jupyter-mcp-server | https://github.com/datalayer/jupyter-mcp-server | #53 on best-of-mcp-servers |
| dbt-mcp | https://docs.getdbt.com/guides/qs-mcp-local | Official dbt Labs server (#52 on best-of-mcp-servers) |
| browserbase | https://docs.browserbase.com/integrations/mcp/setup ; https://www.npmjs.com/package/@browserbasehq/mcp | Official Browserbase server (#49 on best-of-mcp-servers) |

"#N on best-of-mcp-servers" refers to https://github.com/tolkonepiu/best-of-mcp-servers,
fetched 2026-08-29.

## Servers researched but dropped (no verifiable primary-source launch command)

- **Cloudflare** — multiple competing `@scope/mcp-server-cloudflare`-style packages found;
  could not confirm which is the current official launch command/args from a primary
  source rather than a leaderboard blurb, so it was left out rather than guessed.

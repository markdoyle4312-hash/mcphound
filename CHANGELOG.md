# Changelog

All notable changes to mcpvet are documented here. Format loosely follows
[Keep a Changelog](https://keepachangelog.com/); this project doesn't use
SemVer strictly pre-1.0 (see ROADMAP.md).

## [0.1.0] — 2026-08-29

First public release. Static-only scanning; nothing here ever executes an
MCP server.

### Added
- Config discovery for Claude Desktop/Code, Cursor, Windsurf, Gemini CLI,
  and OpenCode (`.json` and `.jsonc`, including trailing-comma JSON5 style).
- `mcpvet inspect` — lists configured servers without executing them.
- `mcpvet scan` — runs detection rules; `--json`, `--sarif`, `--fail-on`,
  `-o/--output`, and `--deep` (opt-in network-dependent checks).
- SARIF 2.1.0 output for GitHub code scanning.
- Seven static detection rules, each with the required YAML + malicious
  fixture + benign fixture + pytest:
  - `MCP-STATIC-001` — hardcoded secret in server env (LLM02, high)
  - `MCP-STATIC-002` — curl/wget-pipe-to-shell launch command (AST04, critical)
  - `MCP-STATIC-003` — over-broad host/filesystem permissions (LLM08, high)
  - `MCP-STATIC-004` — unpinned or `@latest` package version (AST04, medium)
  - `MCP-STATIC-005` — tool-description injection markers: hidden HTML
    comments, zero-width Unicode, exfiltration-imperative phrasing (LLM01, critical)
  - `MCP-STATIC-006` — typosquat of a known MCP package name, via
    Levenshtein distance against a bundled seed list (AST04, high)
  - `MCP-STATIC-007` — npm package missing a `repository` field in its
    registry metadata; network-dependent, gated behind `--deep` (AST04, medium)

### Fixed
- `_target_text`'s raw-JSON dump used `ensure_ascii=True`, silently hex-escaping
  zero-width Unicode characters before MCP-STATIC-005 could see them.
- `.jsonc` configs with a trailing comma before `}`/`]` (valid JSON5, common
  in hand-edited `opencode.jsonc`) failed to parse; the repo's own
  `opencode.jsonc` hit this.

### Known limitations
- Package provenance (`MCP-STATIC-007`) only checks for a missing npm
  `repository` field. Postinstall-script inspection and registry-age checks
  (both named in ROADMAP.md's W4) are not implemented yet.
- The typosquat reference list (`src/mcpvet/rules/data/known_servers.yaml`)
  is a small hand-curated seed, not the official registry — Phase 2's
  registry poller will supersede it.
- PyPI packages (`uvx`-launched) aren't covered by MCP-STATIC-007 yet, only
  npm/`npx`.

### Dogfood / canary results
- `mcpvet scan .mcp.json opencode.jsonc --fail-on high`: zero findings against
  this repo's own agent configs.
- `mcpvet scan --deep` against 5 well-known real MCP packages
  (`@modelcontextprotocol/server-filesystem`, `-postgres`, `-everything`,
  `@upstash/context7-mcp`, `@playwright/mcp`): one genuine finding —
  `@modelcontextprotocol/server-postgres` has no `repository` field in its
  npm metadata (confirmed against the live registry; the package is also
  marked deprecated on npm, unrelated to this rule but worth knowing).
  No previous release to diff against — this is the baseline.

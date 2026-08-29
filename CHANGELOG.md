# Changelog

All notable changes to mcphound are documented here. Format loosely follows
[Keep a Changelog](https://keepachangelog.com/); this project doesn't use
SemVer strictly pre-1.0 (see ROADMAP.md).

## [Unreleased]

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

mcpvet discovers the MCP servers configured in your AI coding clients
(Claude Desktop/Code, Cursor, Windsurf, Gemini CLI, OpenCode — both `.json`
and JSON5-style `.jsonc`) and runs a set of static detection rules against
each server's launch command, environment, and (optionally) npm registry
metadata. Every finding maps to an OWASP LLM Top 10 or Agentic/MCP Top 10
code. Output is human-readable by default, or `--json` / `--sarif` for
tooling and GitHub code scanning, with `--fail-on` exit codes for CI.

Install and run (published on PyPI as `mcphound`; `mcpvet` is kept as a
back-compat command alias):

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
- `mcpvet inspect` — lists configured servers without executing them.
- `mcpvet scan` — runs detection rules; `--json`, `--sarif`, `--fail-on`,
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
- The typosquat reference list (`src/mcpvet/rules/data/known_servers.yaml`)
  is a small hand-curated seed, not the official registry — Phase 2's
  registry poller will supersede it.
- PyPI packages (`uvx`-launched) aren't covered by MCP-STATIC-007 yet, only
  npm/`npx`.
- The PyPI *distribution name* is `mcphound`, not `mcpvet`. `mcpvet` on
  PyPI belongs to an unrelated package; `mcp-vet` was rejected by PyPI as
  "too similar to an existing project" (its name-similarity check strips
  hyphens/underscores before comparing, so `mcp-vet` collided with
  `mcpvet`); `mcpaudit` belongs to a different, actively-maintained MCP
  security scanner. The importable module and CLI command are still
  `mcpvet` — `pip install mcphound` installs both the `mcphound` and
  `mcpvet` commands (same entry point), so `uvx mcphound scan` and
  `uvx --from mcphound mcpvet scan` both work.

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

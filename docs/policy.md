# mcp-policy.yaml

An allowlist of the MCP servers a repo expects, enforced by `mcphound
allowlist enforce`. Complements `mcphound scan` (observational) by letting
a repo declare and enforce which servers are allowed to be present at all.

## Quickstart

```bash
mcphound allowlist init      # writes mcp-policy.yaml + mcp-policy-baseline.json
mcphound allowlist enforce   # checks the current config(s) against them
```

## Schema

```yaml
mode: baseline          # baseline | strict — see "Modes" below
fail_on: medium         # low | medium | high | critical — same scale as `scan --fail-on`

blocked_registries:
  - "shady-mirror.example.com"     # substring match vs. docker image refs / server URLs

servers:
  - name: "@modelcontextprotocol/server-filesystem"
    version: "1.2.3"      # set version for an npm/pypi-launched server...
  - name: "ghcr.io/acme/mcp-tool"
    digest: "sha256:abcd..."   # ...or digest for a docker-launched one. Never both on one entry.
```

A server's `name` is its resolved identity: the npm/pypi package name for
an `npx`/`uvx` launch, the image name (tag/digest stripped) for a `docker
run` launch, or the URL host for an `http`-transport server. `mcphound
allowlist init` fills this in for you from whatever's currently
configured.

## Two independent checks

1. **Allowlist** (`servers:` / `blocked_registries:`) — is every
   discovered server on the list, at the version/digest it declares, and
   not from a blocked registry? Always enforced, regardless of `mode`.
   Grandfathering "which servers may exist" would defeat the point of an
   allowlist.
2. **Findings** — the same severity gate `scan --fail-on` applies, but
   which findings count depends on `mode`.

## Modes

- `strict` — every current finding at or above `fail_on` fails the check.
- `baseline` — only findings that weren't already present when
  `mcp-policy-baseline.json` was last written fail the check. This is the
  fix for the classic brownfield-linter-adoption problem: adopting this on
  an existing repo with pre-existing findings shouldn't mean a wall of red
  on day one unrelated to your change.

Worked example: you run `allowlist init` on a repo with one server that
has an existing medium-severity finding. `enforce` passes clean (it's
baselined). A teammate's PR adds a second, unpinned server. `enforce`
fails — but only reports the *new* server as unlisted; the original
server's pre-existing finding stays quiet.

## Commands

### `mcphound allowlist init`

Scans the current config(s) (same auto-discovery `mcphound scan` uses),
writes `mcp-policy.yaml` (`mode: baseline`, every discovered server
allowlisted at its current version/digest) and `mcp-policy-baseline.json`
(every current finding). Refuses to overwrite either file unless `--force`
is passed.

### `mcphound allowlist enforce [CONFIG...]`

Same config-discovery flags as `mcphound scan` (`--self`, `--deep`,
`--json`, `-o/--output`). Exits 1 if any violation survives baseline
filtering, or if an explicitly-named config file is missing. `--json`
output is a list of violation objects:

```json
[
  {
    "kind": "unlisted_server",
    "server": "@acme/new-tool",
    "rule_id": null,
    "severity": "high",
    "detail": "\"@acme/new-tool\" is not in the mcp-policy.yaml allowlist"
  }
]
```

`kind` is one of `unlisted_server`, `version_drift`, `blocked_registry`,
or `finding`.

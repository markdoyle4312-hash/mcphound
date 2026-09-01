# mcphound GitHub Action

Enforces `mcp-policy.yaml` (see [docs/policy.md](policy.md)) on every pull
request: posts a sticky comment with the check result and fails the PR
check on any violation.

## Usage

```yaml
# .github/workflows/mcphound.yml
name: mcphound allowlist check
on: pull_request

jobs:
  allowlist-check:
    runs-on: ubuntu-latest
    permissions:
      pull-requests: write
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: markdoyle4312-hash/mcphound@v0.1.5
```

> No `v1` tag exists yet — see "Publishing status" below. Pin to the
> latest release tag (currently `v0.1.5`) until `v1` is cut.

`fetch-depth: 0` (or at least enough history to reach the PR's base
commit) is required — the action diffs the PR against its base to decide
whether any MCP config changed.

## Inputs

| Input | Default | Description |
|---|---|---|
| `version` | `0.1.5` | Pinned mcphound version to run. Bump deliberately — never left at a floating "latest". |
| `config-path` | *(empty)* | Explicit config file path. Empty means auto-discovery of this repo's own configs (`--self`). |
| `policy-path` | `mcp-policy.yaml` | Path to the policy file. |
| `baseline-path` | `mcp-policy-baseline.json` | Path to the findings baseline. |
| `github-token` | `${{ github.token }}` | Token used to post the PR comment. |

## Behavior

- No `mcp-policy.yaml` in the repo yet → posts a comment suggesting
  `mcphound allowlist init`, doesn't fail the check.
- No MCP config file changed in this PR → skips entirely, no comment, no
  failure.
- Violations found → sticky comment with the full table, check fails.
- Clean → sticky comment says "No violations," check passes. A
  previously-failing PR that gets fixed updates the same comment rather
  than leaving a stale failure behind.

## Publishing status

This action is not yet listed on the GitHub Marketplace. Cutting a `v1`
tag and publishing via the repo's GitHub UI ("Draft a release" →
"Publish this Action to the Marketplace") is a manual, one-time step,
done once this has run cleanly against a few real adopting repos.

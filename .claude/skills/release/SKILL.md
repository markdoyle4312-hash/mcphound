---
name: release
description: Use before cutting a release of mcphound or publishing the GitHub Action. Full pre-flight checklist.
---

# Release checklist

1. `uv run pytest -q` — all green.
2. `uv run ruff check .` — clean.
3. `uv run mcphound scan .mcp.json opencode.jsonc --fail-on high` — scanner passes over the repo's own agent configs (dogfood, same command as `make scan-self`). Zero unacknowledged high/critical findings.
4. Scan the 5 most-downloaded community MCP servers as a canary batch; compare scores to previous release — document any score changes in CHANGELOG.
5. SARIF output verified to load in GitHub code scanning (test on a throwaway branch).
6. Version bumped in `pyproject.toml`; CHANGELOG entry with Conventional Commits. Since `main` has `enforce_admins` branch protection (2026-08-30), the version-bump commit lands via a PR (branch → push → PR → wait for the 5 required checks → merge), not a direct push — only then tag `vX.Y.Z` off the merged commit.
7. GitHub Action's `action.yml` references the new version (or `@v1` major tag moved intentionally).
8. Release notes include: new rule ids, OWASP mapping changes, any breaking output-format changes.
9. **Human runs the publish commands** — the agent prepares everything but never executes `uv publish`, `git push --tags`, or marketplace publish without approval.

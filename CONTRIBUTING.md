# Contributing to mcphound

mcphound is solo-maintained, pre-1.0 — see [GOVERNANCE.md](GOVERNANCE.md) for
the actual review process and turnaround expectations. This file is the
practical "how do I get set up and send a PR" doc; read GOVERNANCE.md too if
you're proposing a detection rule.

By participating, you're expected to follow the
[Code of Conduct](CODE_OF_CONDUCT.md).

## Dev setup

```bash
uv sync --extra dev      # or --all-extras for registry/api work too
uv run pytest -q         # tests
uv run ruff check .      # lint
uv run mypy src/mcphound # type check (make typecheck also syncs registry+api extras)
make scan-self            # dogfood: scan this repo's own agent configs
```

`pre-commit install` picks up `.pre-commit-config.yaml` (ruff, gitleaks,
mypy, and the mcphound self-scan hook) if you want checks on every commit
rather than just in CI.

## What kind of change you're making

- **New or changed detection rule** — go to [GOVERNANCE.md](GOVERNANCE.md)
  first. Every rule needs all four artifacts (YAML rule, malicious fixture,
  benign fixture, pytest) — see `.claude/skills/rule-authoring/SKILL.md` for
  the schema and numbering convention. Open a "New detection rule proposal"
  issue before the PR if the attack pattern isn't obvious from an existing
  CVE/disclosure.
- **Bug fix / small change** — a PR is fine without a prior issue. Explain
  what broke and how you found it.
- **Anything touching the registry poller, API, or site** — mention it in
  the PR description; those paths have their own CI jobs (`db-tests`,
  `site-build`) that need to stay green.

## Before opening a PR

- `uv run pytest -q`, `uv run ruff check .`, and `uv run mypy src/mcphound`
  all pass locally.
- No secrets, real API keys, or working exfiltration endpoints anywhere —
  fixtures use `MCPHOUND-FIXTURE-CANARY` and RFC2606 domains
  (`example.com`/`.test`) per [CLAUDE.md](CLAUDE.md)'s safety rules.
- `CHANGELOG.md` updated if the change is user-visible.
- The PR template's checklist is filled in — it mirrors this list and
  GOVERNANCE.md's rule-review checklist.

## Safety rules for this codebase

This project handles malware-adjacent code. In particular: **never execute a
fixture MCP server on the host** (no `npx`/`uvx`/`node`/`python` against
anything in `tests/fixtures/` outside Docker) — see the SAFETY RULES section
of [CLAUDE.md](CLAUDE.md) before writing anything that touches
`tests/fixtures/` or the dynamic-analysis sandbox.

## Review and merge

`main` is protected — even the maintainer merges via PR, not a direct push.
A PR that meets the bar above gets merged; one that doesn't gets specific
feedback, not a silent close. There's no SLA (solo-maintained), but a
submission that doesn't get fixed stays open rather than getting closed for
inactivity.

## Reporting a security vulnerability

Don't open a public issue — see [SECURITY.md](SECURITY.md) for private
disclosure.

## Reporting a false positive in an existing rule

```bash
mcphound feedback <rule-id> --note "why you think this is wrong"
```

See [GOVERNANCE.md](GOVERNANCE.md#false-positives).

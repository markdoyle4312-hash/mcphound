# Community governance

mcphound is solo-maintained, pre-launch. This document is the actual process a
contribution gets held to, not aspirational notes.

## Proposing a new detection rule

1. **Open an issue first**, using the "New detection rule proposal" template (or
   check existing issues/PRs to avoid duplicate work). Describe the attack
   pattern, a primary-source reference (a disclosure, CVE, or research note —
   per CLAUDE.md, prefer primary sources over blog paraphrases), and roughly
   what the detection would key on.
2. Once the approach looks sound, **open a PR** with all four required
   artifacts. This is non-negotiable — see
   `.claude/skills/rule-authoring/SKILL.md` for the exact YAML schema, fixture
   layout, and numbering convention:
   - The YAML rule (`src/mcphound/rules/<id>.yaml`)
   - A malicious fixture that triggers it
   - A benign fixture that doesn't (the false-positive guard)
   - A pytest asserting both
3. The PR template's checklist mirrors this list — use it.

### What a review actually checks

- **OWASP mapping present** (`LLMxx` or `ASTxx`) — no uncategorized findings, per
  CLAUDE.md's non-negotiable engineering rules.
- **The benign fixture is a genuinely close call**, not a strawman. A benign
  fixture that looks nothing like the malicious one doesn't guard against
  anything.
- **No false positives against the real-world corpus**: run
  `uv run pytest tests/fp_sweep -q`. A new rule that fires on any server in
  `tests/fp_sweep/registry_top50.json` needs to either be narrowed, or come
  with a documented reason those servers are correctly flagged (see
  `CHANGELOG.md`'s W7 entry for what that documentation looks like).
- **Network calls are marked and gated**: any `detect` that hits the network
  sets `network: true` at the rule's top level (see the `npm_provenance`
  pattern in `rules/engine.py`) — `cli.py` filters such rules out unless
  `--deep` is passed. The HTTP call itself lives in its own function so tests
  can `monkeypatch` it; pytest must never make a live network call.
- **Doesn't duplicate an existing rule's coverage** — if two rules would fire
  on the same pattern, tighten or merge one instead of adding a third.
- **Severity/confidence are justified**, not copy-pasted from a neighboring
  rule — see the existing rules in `src/mcphound/rules/` for the range in use.

### Turnaround

Best-effort, solo-maintained — there's no SLA. A PR that meets the bar above
gets merged; one that doesn't gets specific feedback on what's missing, not a
silent close. A submission that doesn't meet the bar and doesn't get fixed
stays open rather than getting closed for inactivity.

## Responsible disclosure
- If your scan finds a live malicious MCP server or skill: do NOT open a public issue naming it immediately. Email maintainers first; we coordinate with the affected registry (the official MCP Registry, npm, PyPI) and publish after takedown or 30 days, whichever is sooner.
- Test payloads use canary markers (`MCPHOUND-FIXTURE-CANARY`) and RFC2606 domains (`example.com`); never working exfiltration against real services.

## False positives
- Report via `mcphound feedback <rule-id> [--note "..."]` — it prints a pre-filled GitHub issue URL (no network call, no auth) with the rule, your mcphound version, and a place to paste a redacted config snippet. Or file a GitHub issue directly with the config. FP fixes are release-blockers; they get changelog entries.

## Security policy
- Security reports: see [SECURITY.md](SECURITY.md).

# Community governance (working notes — expand before v0.1 launch)

## Contributing rules
- Detection rules are data: add `src/mcpvet/rules/*.yaml` + fixtures + tests (see `.claude/skills/rule-authoring/SKILL.md`).
- Every rule needs an OWASP mapping and a benign false-positive fixture.
- Rules that rely on network calls or an LLM must be marked non-deterministic and separable from the default free scan.

## Responsible disclosure
- If your scan finds a live malicious MCP server or skill: do NOT open a public issue naming it immediately. Email maintainers first; we coordinate with the affected registry (the official MCP Registry, npm, PyPI) and publish after takedown or 30 days, whichever is sooner.
- Test payloads use canary markers (`MCPVET-FIXTURE-CANARY`) and RFC2606 domains (`example.com`); never working exfiltration against real services.

## False positives
- Report via `--feedback` (to be built) or GitHub issues with the config. FP fixes are release-blockers; they get changelog entries.

## Security policy
- Security reports: SECURITY.md at launch (use GitHub private advisories until then).

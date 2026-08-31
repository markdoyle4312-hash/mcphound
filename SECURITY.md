# Security policy

mcphound is solo-maintained (see [GOVERNANCE.md](GOVERNANCE.md)) — reports get
a best-effort response, not an SLA, but every valid report gets a fix or a
documented reason it isn't one.

## Reporting a vulnerability in mcphound itself

Use **[GitHub private vulnerability reporting](https://github.com/markdoyle4312-hash/mcphound/security/advisories/new)**
("Security" tab → "Report a vulnerability") so the report and any discussion
stay private until a fix ships. If you can't use that, email
mark.doyle4312@gmail.com instead.

Include:
- Affected component (CLI, rule engine, registry poller, API, site, GitHub
  Action) and version (`mcphound --version`, or the pinned `version` input
  for the Action).
- Steps to reproduce, or a PoC. Test payloads should carry the
  `MCPHOUND-FIXTURE-CANARY` marker and use RFC2606 domains
  (`example.com`/`.test`) rather than live exfiltration against real
  services — see the Safety section of [CLAUDE.md](CLAUDE.md).
- Impact as you see it (e.g. "a crafted `.mcp.json` causes RCE during static
  scanning" is critical; "a rule under-reports a known bypass" is a
  detection-quality bug, not a security report — file those as a normal
  issue instead, or via `mcphound feedback`).

Do not open a public issue for an unpatched vulnerability.

## Scope

In scope: the `mcphound` CLI and rule engine, the registry poller, the
read-only API, the GitHub Action, and the public site's server-side code.

Out of scope: findings *about* third-party MCP servers surfaced by a scan —
those follow the "live malicious server" process in
[GOVERNANCE.md](GOVERNANCE.md#responsible-disclosure), not this policy.

**A reminder that applies regardless of scope**: mcphound's static scanner
never executes an MCP server, and its own test fixtures must never be run
outside the sandbox — see CLAUDE.md's safety rules before building a repro
against this repo's `tests/fixtures/`.

## Supported versions

Pre-1.0, solo-maintained: only the latest published release on
[PyPI](https://pypi.org/project/mcphound/) receives fixes. There is no
backport policy yet.

## Disclosure timeline

No fixed embargo, but the working default is: acknowledge within a few days,
fix or mitigate, then publish a GitHub security advisory crediting the
reporter (unless they ask to stay anonymous) once a fix is out.

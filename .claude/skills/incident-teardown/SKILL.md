---
name: incident-teardown
description: Use when a new MCP/agent-supply-chain attack or worm is disclosed (e.g. another Miasma/ClawHavoc). Produces the analysis-to-rule pipeline.
---

# Turning a disclosed attack into detections (fast)

Speed matters — being first with a public analysis is the distribution playbook.

1. **Collect primary sources**: the disclosing lab's blog (Invariant, Koi, Snyk, OX, UpGuard, Antiy CERT), CVE if assigned, sample configs/IOCs, OWASP/CSA analysis. Save URLs.
2. **Extract the kill chain** into `docs/incidents/<date>-<name>.md`: initial access (registry entry? repo PR?), poisoning technique (which field, what markers), action (credential theft? config rewrite?), persistence.
3. **Write detection rule(s)** using the `rule-authoring` skill:
   - Static: match the IOC/pattern (e.g. specific config-rewrite path, hidden comment style, endpoint).
   - Dynamic: what egress/tool-shadowing behavior did it exhibit? Add a sandbox assertion.
4. **Build fixtures from the real IOCs** (sanitized, canary-marked) — real attacks make the best regression tests.
5. **Publish**: short public teardown on the site/blog, X/LinkedIn thread, HN if novel, responsible-disclosure email to affected registries. Include "detected by mcpvet rule MCP-xxx" in the post with a link to the server's reputation page.
6. Bump version per `release-checklist` if the rule is time-critical (patch release).

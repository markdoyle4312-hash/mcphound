---
name: rule-authoring
description: Use when adding a new detection rule to mcpvet (static or dynamic). Covers the YAML rule schema, fixtures, OWASP mapping, and tests.
---

# Authoring a new mcpvet detection rule

Every rule MUST land with four artifacts: YAML rule, malicious fixture, benign fixture, pytest.

## 1. Rule file: `src/mcpvet/rules/<id>.yaml`

```yaml
id: MCP-STATIC-007
title: Dangerous install command (curl pipe shell)
owasp: LLM01            # LLMxx = OWASP LLM Top10, ASTxx = OWASP Agentic Top10
phase: static           # static | dynamic
severity: high           # low | medium | high | critical
confidence: high
description: >
  MCP server launch commands that pipe a remote script into a shell
  execute attacker-controlled code at startup.
detect:
  field: command          # which field of the server config to inspect
  pattern: '(curl|wget)\s+[^\s|]+\s*\|\s*(sh|bash|zsh)'
recommendation: Vendor the script or use a pinned package from a registry.
references:
  - https://invariantlabs.ai/blog/mcp-security-notification-tool-poisoning-attacks
```

## 2. Fixtures
- Malicious: `tests/fixtures/static/<id>/mcp.json` — contains the triggering pattern AND the canary string `MCPVET-FIXTURE-CANARY` somewhere in a comment.
- Benign: `tests/fixtures/static/<id>/benign-mcp.json` — the closest legitimate config (false-positive guard). For install-command rules, a pinned `npx -y pkg@1.2.3`.

## 3. Test: `tests/rules/test_<id>.py`
- Assert the malicious fixture fires with the exact rule id and severity.
- Assert the benign fixture does NOT fire the rule.
- Assert OWASP code is present in the JSON output.

## 4. Before you commit
- `uv run pytest tests/rules/ -q` passes.
- Run `uv run mcpvet scan tests/fixtures/static/<id>/mcp.json --json` and eyeball the output.
- Rule is registered in the rules index (`src/mcpvet/rules/index.py` if needed).
- Never run the malicious fixture's server — static rules never execute anything. Dynamic rules only execute inside the Docker sandbox runner.

## Rule numbering convention
- `MCP-STATIC-0xx` static config/package checks
- `MCP-DYNAMIC-0xx` sandbox runtime checks
- `SKILL-0xx` agent-skill/tool-description language checks

---
name: rule-authoring
description: Use when adding a new detection rule to mcphound (static or dynamic). Covers the YAML rule schema, fixtures, OWASP mapping, and tests.
---

# Authoring a new mcphound detection rule

Every rule MUST land with four artifacts: YAML rule, malicious fixture, benign fixture, pytest.

## 1. Rule file: `src/mcphound/rules/<id>.yaml`

```yaml
id: MCP-STATIC-0xx        # next unused number — check src/mcphound/rules/ before picking one
title: Dangerous install command (curl pipe shell)
owasp: LLM01            # LLMxx = OWASP LLM Top10, ASTxx = OWASP Agentic Top10
phase: static           # static | dynamic
severity: high           # low | medium | high | critical
confidence: high
description: >
  MCP server launch commands that pipe a remote script into a shell
  execute attacker-controlled code at startup.
detect:
  target: command          # which field of the server config to inspect: command | url | env | raw
  pattern: '(curl|wget)\s+[^\s|]+\s*\|\s*(sh|bash|zsh)'
recommendation: Vendor the script or use a pinned package from a registry.
references:
  - https://invariantlabs.ai/blog/mcp-security-notification-tool-poisoning-attacks
```

Most detections are a regex against `target` text — that's "rules are data, not code." One
exception exists: **typosquat checks need edit-distance, not a regex**, so they use a second
`detect` shape with dedicated engine support in `rules/engine.py`:

```yaml
detect:
  type: typosquat
  target: command                        # only "command" is supported today
  reference_list: known_servers.yaml     # YAML list under src/mcphound/rules/data/
  max_distance: 2                        # flag names within N edits of a reference name,
                                          # but not an exact match (exact = it IS that package)
```

A third exists for checks that need live registry data — **npm provenance**:

```yaml
network: true             # REQUIRED alongside this detect.type — see below
detect:
  type: npm_provenance
  target: command          # only npx-launched packages are checked
```

Any rule whose `detect` needs the network (not just this one) MUST set the top-level `network: true`
field. `cli.py`'s `_collect()` filters those rules out unless `--deep` is passed — per
GOVERNANCE.md, network-dependent checks must be marked and kept separable from the default free
scan. The actual HTTP call must live in its own small function (see `_fetch_npm_metadata` in
`rules/engine.py`) so tests can `monkeypatch` it instead of hitting the real registry — `pytest`
must never make live network calls.

Don't add a fourth `detect.type` casually — every new type is engine code, not a community-PR-able
YAML rule. Prefer extending the regex path unless the check is genuinely not regex-expressible.

## 2. Fixtures
- Malicious: `tests/fixtures/static/<id>/mcp-malicious.json` — contains the triggering pattern AND the canary string `MCPHOUND-FIXTURE-CANARY` somewhere in the file.
- Benign: `tests/fixtures/static/<id>/mcp-benign.json` — the closest legitimate config (false-positive guard). For install-command rules, a pinned `npx -y pkg@1.2.3`.

## 3. Test: add cases to `tests/test_rules.py`
- Use the `_finding_ids(fixture, rule_dir)` helper already in that file.
- Assert the malicious fixture fires with the exact rule id.
- Assert the benign fixture does NOT fire the rule.
- The existing `test_every_finding_is_owasp_mapped` / `test_sarif_serializes` cases cover OWASP-code presence and SARIF validity for all rules automatically — no per-rule duplication needed.

## 4. Before you commit
- `uv run pytest tests/test_rules.py -q` passes.
- Run `uv run mcphound scan tests/fixtures/static/<id>/mcp-malicious.json --json` and eyeball the output.
- No separate rule index to update — `rules/loader.py` globs every `*.yaml` in `src/mcphound/rules/` automatically.
- Run `make docs` (or `uv run python scripts/generate_rule_docs.py`) to regenerate `docs/rules.md` from the rule YAML — CI's `docs-check` job fails the build if it's stale.
- Never run the malicious fixture's server — static rules never execute anything. Dynamic rules only execute inside the Docker sandbox runner.

## Rule numbering convention
- `MCP-STATIC-0xx` static config/package checks
- `MCP-DYNAMIC-0xx` sandbox runtime checks
- `SKILL-0xx` agent-skill/tool-description language checks

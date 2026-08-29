## What does this PR do?

<!-- One or two sentences. Link the issue if there's a "new rule proposal" discussion. -->

## If this adds or changes a detection rule

- [ ] `src/mcphound/rules/<id>.yaml` — OWASP mapping set (`LLMxx`/`ASTxx`), `network: true` set if it calls out
- [ ] Malicious fixture (`tests/fixtures/static/<id>/mcp-malicious.json`) — contains `MCPHOUND-FIXTURE-CANARY`, never referenced from any real agent config
- [ ] Benign fixture (`tests/fixtures/static/<id>/mcp-benign.json`) — the closest legitimate config, not a strawman
- [ ] Test added to `tests/test_rules.py` asserting the malicious fixture fires and the benign one doesn't
- [ ] `uv run pytest tests/fp_sweep -q` passes — no new false positive against the real-world corpus
- [ ] `make docs` run, `docs/rules.md` committed if it changed

See `.claude/skills/rule-authoring/SKILL.md` and `GOVERNANCE.md` for the full requirements.

## Checklist

- [ ] `uv run pytest -q` passes locally
- [ ] `uv run ruff check .` passes locally
- [ ] No secrets or real credentials anywhere in fixtures or code
- [ ] `CHANGELOG.md` updated if this is user-visible

#!/usr/bin/env python3
"""CI gate: every detection rule must ship with all four required artifacts.

Per CLAUDE.md's non-negotiable engineering rules and
`.claude/skills/rule-authoring/SKILL.md`, a rule isn't done until it has:
  1. A YAML rule file (src/mcphound/rules/<id>.yaml) — enforced implicitly,
     since this script starts from the loaded rule list.
  2. At least one malicious fixture (tests/fixtures/static/<id>/mcp-malicious*.json).
  3. At least one benign fixture (tests/fixtures/static/<id>/mcp-benign*.json) —
     the false-positive guard.
  4. A pytest that references the rule id (heuristic: the id string appears at
     least twice in tests/ — once for the "fires" assertion, once for "doesn't
     fire" — since a single mention is usually just an OWASP/SARIF sweep test
     that isn't specific to this rule).

This was previously just a written checklist (GOVERNANCE.md, the PR template)
with no automated check — a rule could land missing one of the four and
nothing would catch it. Run via `make rules-check`.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from mcphound.rules.loader import load_rules  # noqa: E402

FIXTURES_DIR = REPO_ROOT / "tests" / "fixtures" / "static"
TESTS_DIR = REPO_ROOT / "tests"


def _test_file_text() -> str:
    return "\n".join(p.read_text(encoding="utf-8") for p in TESTS_DIR.rglob("*.py"))


def check_rule(rule_id: str, all_tests_text: str) -> list[str]:
    problems = []
    fixture_dir = FIXTURES_DIR / rule_id

    if not fixture_dir.is_dir():
        problems.append(f"no fixture directory {fixture_dir.relative_to(REPO_ROOT)}")
        return problems

    if not list(fixture_dir.glob("mcp-malicious*.json")):
        problems.append(f"missing malicious fixture in {fixture_dir.relative_to(REPO_ROOT)}")
    if not list(fixture_dir.glob("mcp-benign*.json")):
        problems.append(f"missing benign fixture in {fixture_dir.relative_to(REPO_ROOT)}")

    if all_tests_text.count(rule_id) < 2:
        problems.append(
            f"'{rule_id}' appears fewer than 2 times under tests/ "
            "(expected at least a 'fires' and a 'does not fire' assertion)"
        )

    return problems


def main() -> int:
    rules = load_rules()
    all_tests_text = _test_file_text()

    failures: dict[str, list[str]] = {}
    for rule in rules:
        problems = check_rule(rule["id"], all_tests_text)
        if problems:
            failures[rule["id"]] = problems

    if not failures:
        print(f"OK: all {len(rules)} rules have their required artifacts.")
        return 0

    print("Rules missing required artifacts (see .claude/skills/rule-authoring/SKILL.md):\n")
    for rule_id, problems in sorted(failures.items()):
        print(f"  {rule_id}:")
        for problem in problems:
            print(f"    - {problem}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

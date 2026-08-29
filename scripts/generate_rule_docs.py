#!/usr/bin/env python3
"""Generate docs/rules.md from src/mcphound/rules/*.yaml.

The rule catalog is generated, not hand-written, so it can never drift from the
actual rules — see CLAUDE.md: "Rules are data, not code." Run this after adding or
editing a rule:

    uv run python scripts/generate_rule_docs.py

CI (`make docs-check`) re-runs it and fails if the working tree then has a diff,
so a stale docs/rules.md can't land on main.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from mcphound.rules.loader import load_rules  # noqa: E402

OUT_PATH = REPO_ROOT / "docs" / "rules.md"


def _detect_summary(rule: dict) -> str:
    detect = rule.get("detect") or {}
    detect_type = detect.get("type")
    if detect_type == "typosquat":
        target = detect.get("target", "command")
        return (
            f"Levenshtein distance ≤ {detect.get('max_distance', 2)} from a name in "
            f"`{detect.get('reference_list', '?')}`, checked against `{target}`"
        )
    if detect_type == "npm_provenance":
        return "npm registry lookup for the launched package's `repository` field (network)"
    return f"Regex against `{detect.get('target', 'command')}`"


def _rule_row(rule: dict) -> str:
    network = "yes" if rule.get("network") else ""
    return (
        f"| [`{rule['id']}`](#{rule['id'].lower()}) | {rule.get('title', '')} "
        f"| {rule.get('severity', '')} | {rule.get('confidence', '')} "
        f"| {rule.get('owasp', '')} | {network} |"
    )


def _rule_section(rule: dict) -> str:
    lines = [
        f"## {rule['id']}",
        "",
        f"**{rule.get('title', '')}**",
        "",
        f"- Severity: `{rule.get('severity', '')}`",
        f"- Confidence: `{rule.get('confidence', '')}`",
        f"- OWASP mapping: `{rule.get('owasp', '')}`",
        f"- Phase: `{rule.get('phase', 'static')}`",
        f"- Network-dependent: {'yes, `--deep` only' if rule.get('network') else 'no'}",
        f"- Detection: {_detect_summary(rule)}",
        "",
        (rule.get("description") or "").strip(),
        "",
        f"**Recommendation:** {rule.get('recommendation', '')}",
    ]
    references = rule.get("references") or []
    if references:
        lines += ["", "References:"] + [f"- {ref}" for ref in references]
    return "\n".join(lines)


def render(rules: list[dict]) -> str:
    rules = sorted(rules, key=lambda r: r["id"])
    header = [
        "# mcphound detection rule catalog",
        "",
        "Generated from `src/mcphound/rules/*.yaml` by `scripts/generate_rule_docs.py` —",
        "do not hand-edit; run the generator after changing a rule instead. Every rule",
        "maps to an OWASP LLM Top 10 (`LLMxx`) or Agentic/MCP Top 10 (`ASTxx`) code; see",
        "`.claude/skills/rule-authoring/SKILL.md` for how to add one.",
        "",
        "| Rule | Title | Severity | Confidence | OWASP | Network? |",
        "|---|---|---|---|---|---|",
    ]
    table = [_rule_row(r) for r in rules]
    sections = "\n\n---\n\n".join(_rule_section(r) for r in rules)
    return "\n".join(header + table) + "\n\n\n" + sections + "\n"


def main() -> None:
    rules = load_rules()
    OUT_PATH.write_text(render(rules), encoding="utf-8", newline="\n")
    print(f"Wrote {OUT_PATH} ({len(rules)} rules)")


if __name__ == "__main__":
    main()

"""Load YAML detection rules from src/mcpvet/rules/*.yaml."""

from __future__ import annotations

from pathlib import Path

import yaml

RULES_DIR = Path(__file__).parent


def load_rules(rules_dir: Path | None = None) -> list[dict]:
    rules_dir = rules_dir or RULES_DIR
    rules: list[dict] = []
    for path in sorted(rules_dir.glob("*.yaml")):
        data = yaml.safe_load(path.read_text())
        if isinstance(data, dict) and data.get("id"):
            rules.append(data)
    return rules

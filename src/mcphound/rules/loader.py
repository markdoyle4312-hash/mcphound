"""Load YAML detection rules from src/mcphound/rules/*.yaml."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import yaml

RULES_DIR = Path(__file__).parent


def load_rules(rules_dir: Path | None = None) -> list[dict]:
    rules_dir = rules_dir or RULES_DIR
    rules: list[dict] = []
    for path in sorted(rules_dir.glob("*.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        if isinstance(data, dict) and data.get("id"):
            rules.append(data)
    return rules


def rules_fingerprint(rules: list[dict]) -> str:
    """Stable content hash of a loaded rule set.

    Used as the registry-scan staleness key instead of the mcphound package
    version: the package can (and does, on this project — several point
    releases a day pre-1.0) bump for reasons unrelated to detection logic
    (docs, CI, packaging fixes), and keying staleness off `__version__`
    forces a full ~25k-version rescan on every such release, which is what
    blew a nightly run past GitHub Actions' 6h job limit. Keying off the
    rules themselves means only an actual rule change (the thing that could
    change a finding) triggers a full rescan.
    """
    ordered = sorted(rules, key=lambda rule: rule.get("id", ""))
    digest = hashlib.sha256(json.dumps(ordered, sort_keys=True, default=str).encode()).hexdigest()
    return f"rules-{digest[:16]}"

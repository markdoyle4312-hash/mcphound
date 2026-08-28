"""Output formatters: JSON and SARIF 2.1.0 (GitHub code scanning)."""

from __future__ import annotations

from .models import ScanResult

_SARIF_LEVEL = {"low": "note", "medium": "warning", "high": "error", "critical": "error"}


def to_json(result: ScanResult) -> str:
    return result.model_dump_json(indent=2)


def to_sarif(result: ScanResult) -> dict:
    rules: dict[str, dict] = {}
    sarif_results: list[dict] = []
    for f in result.findings:
        rules.setdefault(
            f.rule_id,
            {
                "id": f.rule_id,
                "name": f.title,
                "shortDescription": {"text": f.title},
                "properties": {"security-severity": f.severity, "owasp": f.owasp},
            },
        )
        sarif_results.append(
            {
                "ruleId": f.rule_id,
                "level": _SARIF_LEVEL.get(f.severity, "warning"),
                "message": {"text": f"{f.title} — {f.detail}"},
                "locations": [
                    {"physicalLocation": {"artifactLocation": {"uri": f.location or "config"}}}
                ],
            }
        )
    return {
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "mcpvet",
                        "informationUri": "https://github.com/your-org/mcpvet",  # update on launch
                        "rules": list(rules.values()),
                    }
                },
                "results": sarif_results,
            }
        ],
    }

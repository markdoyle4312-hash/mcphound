"""Output formatters: JSON and SARIF 2.1.0 (GitHub code scanning)."""

from __future__ import annotations

from .models import ScanResult

_SARIF_LEVEL = {"low": "note", "medium": "warning", "high": "error", "critical": "error"}
_INFORMATION_URI = "https://github.com/markdoyle4312-hash/mcpvet"
# GitHub's code-scanning ingestion requires security-severity to be a
# stringified CVSS-like score, not the severity word — see
# https://docs.github.com/code-security/code-scanning/integrating-with-code-scanning/sarif-support-for-code-scanning#security-severity
_SECURITY_SEVERITY = {"low": "2.5", "medium": "5.5", "high": "7.5", "critical": "9.5"}


def to_json(result: ScanResult) -> str:
    return result.model_dump_json(indent=2)


def _artifact_uri(location: str) -> str:
    # location is "<config path> :: <server name>", built for human display
    # (see rules/engine.py); SARIF's artifactLocation.uri must be a URI, so
    # take just the path and normalize Windows separators.
    path = location.split(" :: ", 1)[0] or "config"
    return path.replace("\\", "/")


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
                "properties": {
                    "security-severity": _SECURITY_SEVERITY.get(f.severity, "5.5"),
                    "owasp": f.owasp,
                },
            },
        )
        sarif_results.append(
            {
                "ruleId": f.rule_id,
                "level": _SARIF_LEVEL.get(f.severity, "warning"),
                "message": {"text": f"{f.title} ({f.server}) — {f.detail}"},
                "locations": [
                    {"physicalLocation": {"artifactLocation": {"uri": _artifact_uri(f.location)}}}
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
                        "name": "mcphound",
                        "informationUri": _INFORMATION_URI,
                        "rules": list(rules.values()),
                    }
                },
                "results": sarif_results,
            }
        ],
    }

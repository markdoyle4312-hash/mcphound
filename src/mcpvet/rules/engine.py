"""Evaluate detection rules against parsed server configurations.

Static rules only at this stage. A rule's `detect` block:
    target: command | url | env | raw      (which text to inspect)
    pattern: <regex>
    allow_if: <substring>                  (skip match when present on the matched line,
                                            e.g. "${" to allow env-var expansion)
One finding per rule per server (first match wins).
"""

from __future__ import annotations

import json
import re

from ..models import Finding, ServerConfig


def _target_text(server: ServerConfig, target: str) -> str:
    if target == "command":
        return " ".join(server.command)
    if target == "url":
        return server.url or ""
    if target == "env":
        return "\n".join(f"{k}={v}" for k, v in server.env.items())
    return json.dumps(server.raw, sort_keys=True)


def evaluate(server: ServerConfig, rules: list[dict]) -> list[Finding]:
    findings: list[Finding] = []
    for rule in rules:
        if rule.get("phase", "static") != "static":
            continue
        detect = rule.get("detect") or {}
        pattern = detect.get("pattern")
        if not pattern:
            continue
        text = _target_text(server, detect.get("target", "command"))
        allow_if = detect.get("allow_if")
        for match in re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE):
            window = text[max(0, match.start() - 60) : match.end() + 60]
            if allow_if and allow_if in window:
                continue
            findings.append(
                Finding(
                    rule_id=rule["id"],
                    title=rule.get("title", rule["id"]),
                    severity=rule.get("severity", "medium"),
                    confidence=rule.get("confidence", "medium"),
                    owasp=rule.get("owasp", ""),
                    phase="static",
                    server=server.name,
                    location=f"{server.source} :: {server.name}",
                    detail=match.group(0)[:160],
                    recommendation=rule.get("recommendation", ""),
                )
            )
            break
    return findings

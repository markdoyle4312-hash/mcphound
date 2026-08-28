"""Evaluate detection rules against parsed server configurations.

Static rules only at this stage. A rule's `detect` block is one of two shapes:

  Regex (default, `type` omitted):
    target: command | url | env | raw      (which text to inspect)
    pattern: <regex>
    allow_if: <substring>                  (skip match when present on the matched line,
                                            e.g. "${" to allow env-var expansion)

  Typosquat (`type: typosquat`) — needs edit-distance, not a regex, so it has
  dedicated engine support rather than being pure YAML data:
    type: typosquat
    target: command                        (only "command" is supported today)
    reference_list: <file under rules/data/>   (YAML list of known-legitimate package names)
    max_distance: <int>                    (flag names within this Levenshtein distance
                                            of a reference name, but not an exact match)

One finding per rule per server (first match wins).
"""

from __future__ import annotations

import functools
import json
import re
from pathlib import Path

import yaml
from rapidfuzz.distance import Levenshtein

from ..models import Finding, ServerConfig

_DATA_DIR = Path(__file__).parent / "data"


def _target_text(server: ServerConfig, target: str) -> str:
    if target == "command":
        return " ".join(server.command)
    if target == "url":
        return server.url or ""
    if target == "env":
        return "\n".join(f"{k}={v}" for k, v in server.env.items())
    return json.dumps(server.raw, sort_keys=True, ensure_ascii=False)


def _make_finding(rule: dict, server: ServerConfig, detail: str) -> Finding:
    return Finding(
        rule_id=rule["id"],
        title=rule.get("title", rule["id"]),
        severity=rule.get("severity", "medium"),
        confidence=rule.get("confidence", "medium"),
        owasp=rule.get("owasp", ""),
        phase="static",
        server=server.name,
        location=f"{server.source} :: {server.name}",
        detail=detail[:160],
        recommendation=rule.get("recommendation", ""),
    )


def _evaluate_regex(server: ServerConfig, rule: dict, detect: dict) -> list[Finding]:
    pattern = detect.get("pattern")
    if not pattern:
        return []
    text = _target_text(server, detect.get("target", "command"))
    allow_if = detect.get("allow_if")
    findings = []
    for match in re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE):
        window = text[max(0, match.start() - 60) : match.end() + 60]
        if allow_if and allow_if in window:
            continue
        findings.append(_make_finding(rule, server, match.group(0)))
        break
    return findings


@functools.lru_cache
def _load_reference_list(filename: str) -> tuple[str, ...]:
    data = yaml.safe_load((_DATA_DIR / filename).read_text(encoding="utf-8"))
    return tuple(data) if isinstance(data, list) else ()


def _package_name(spec: str) -> str:
    """Strip a trailing "@version" (or "@latest") from an npm-style package spec,
    preserving a scoped package's own leading "@scope/" segment."""
    if spec.startswith("@"):
        slash = spec.find("/")
        if slash == -1:
            return spec
        at = spec.find("@", slash)
    else:
        at = spec.find("@")
    return spec[:at] if at != -1 else spec


def _extract_command_package(server: ServerConfig) -> str | None:
    tokens = server.command
    for i, tok in enumerate(tokens):
        if tok in ("npx", "uvx"):
            for cand in tokens[i + 1 :]:
                if cand.startswith("-"):
                    continue
                return _package_name(cand)
    return None


def _evaluate_typosquat(server: ServerConfig, rule: dict, detect: dict) -> list[Finding]:
    pkg = _extract_command_package(server)
    if not pkg:
        return []
    reference = _load_reference_list(detect.get("reference_list", ""))
    if not reference or pkg in reference:
        return []
    max_distance = int(detect.get("max_distance", 2))
    best = min(reference, key=lambda ref: Levenshtein.distance(pkg, ref))
    distance = Levenshtein.distance(pkg, best)
    if distance == 0 or distance > max_distance:
        return []
    detail = f'"{pkg}" is {distance} edit(s) from known package "{best}"'
    return [_make_finding(rule, server, detail)]


def evaluate(server: ServerConfig, rules: list[dict]) -> list[Finding]:
    findings: list[Finding] = []
    for rule in rules:
        if rule.get("phase", "static") != "static":
            continue
        detect = rule.get("detect") or {}
        if detect.get("type") == "typosquat":
            findings.extend(_evaluate_typosquat(server, rule, detect))
        else:
            findings.extend(_evaluate_regex(server, rule, detect))
    return findings

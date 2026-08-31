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

  npm provenance (`type: npm_provenance`) — queries the public npm registry, so it
  is NOT part of the default free scan (GOVERNANCE.md: network-dependent checks
  must be marked and separable). Any rule using it MUST also set `network: true`;
  `cli.py` filters such rules out unless `--deep` is passed:
    type: npm_provenance
    target: command                        (only npx-launched packages are checked)

A rule may also set `also: oci_pin` alongside its primary `pattern`/`type` — a
secondary check, run only when the primary one found nothing, for launch
commands the primary shape can't express. Today the only such check is
unpinned `docker run <image>` references (no regex can safely tell a docker
flag from an image name across arbitrary `docker run` invocations, so this
gets real parsing rather than a pattern):
    also: oci_pin                          (in addition to `pattern`)

One finding per rule per server (first match wins).
"""

from __future__ import annotations

import json
import re
import time

import httpx

from ..models import Finding, ServerConfig
from .typosquat import extract_command_package, load_reference_list, nearest_match

_NPM_TIMEOUT = 5.0
_NPM_MAX_RETRIES = 3
_NPM_BACKOFF_SECONDS = 0.5


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


def _evaluate_typosquat(server: ServerConfig, rule: dict, detect: dict) -> list[Finding]:
    pkg = extract_command_package(server)
    if not pkg:
        return []
    reference = load_reference_list(detect.get("reference_list", ""))
    match = nearest_match(pkg, reference, int(detect.get("max_distance", 2)))
    if match is None:
        return []
    best, distance = match
    detail = f'"{pkg}" is {distance} edit(s) from known package "{best}"'
    return [_make_finding(rule, server, detail)]


def _fetch_npm_metadata(pkg: str) -> dict | None:
    """Isolated so tests can monkeypatch it instead of hitting the real registry.
    Retries a bounded number of times on HTTP 429 (rate limit) before falling
    back to the existing fail-open behavior — never let a provenance check
    fail closed against an offline/rate-limited registry."""
    for attempt in range(_NPM_MAX_RETRIES):
        try:
            resp = httpx.get(f"https://registry.npmjs.org/{pkg}", timeout=_NPM_TIMEOUT)
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as exc:
            is_last_attempt = attempt == _NPM_MAX_RETRIES - 1
            if exc.response.status_code != 429 or is_last_attempt:
                return None
            time.sleep(_NPM_BACKOFF_SECONDS * (attempt + 1))
        except httpx.HTTPError:
            return None
    return None


# Flags that take a following value token, so it isn't mistaken for the image
# reference (e.g. "docker run -e KEY=VAL image:tag" — "KEY=VAL" isn't the image).
# Not exhaustive — covers common `docker run` flags likely on an MCP server's
# launch command; an unrecognized value-taking flag could still be misread as
# the image, same fail-safe direction as the rest of this rule (a missed image
# just means no finding, never a wrong one).
_OCI_VALUE_FLAGS = {
    "-e", "--env", "--env-file", "-p", "--publish", "-v", "--volume", "--name",
    "-w", "--workdir", "--network", "--entrypoint", "-u", "--user", "--mount",
    "-l", "--label", "--hostname", "-m", "--memory", "--cpus", "--restart",
    "--platform",
}

# A tag that looks like an actual version — same "pinned enough" bar this
# codebase already applies to npm/pypi `pkg@1.2.3` specs, not true digest
# immutability. Anything else (no tag, "latest", or a floating label like
# "mcp"/"stable"/"main") is treated as unpinned.
_SEMVER_TAG = re.compile(r"^v?\d+(\.\d+){0,2}$")


def _oci_image_ref(command: list[str]) -> str | None:
    """First non-flag token after a `docker run` in a command list, skipping
    flags (and their values, for flags known to take one). Returns None if
    there's no `docker run` or nothing but flags follow it."""
    for i, token in enumerate(command):
        if token != "docker" or i + 1 >= len(command) or command[i + 1] != "run":
            continue
        j = i + 2
        while j < len(command):
            candidate = command[j]
            if not candidate.startswith("-"):
                return candidate
            flag = candidate.split("=", 1)[0]
            j += 1
            if "=" not in candidate and flag in _OCI_VALUE_FLAGS:
                j += 1
        return None
    return None


def _evaluate_oci_pin(server: ServerConfig, rule: dict, detect: dict) -> list[Finding]:
    ref = _oci_image_ref(server.command)
    if not ref:
        return []
    if "@sha256:" in ref:
        return []  # digest-pinned: immutable regardless of any tag alongside it
    last_segment = ref.rsplit("/", 1)[-1]  # avoid a registry host's ":port" prefix
    if ":" not in last_segment:
        detail = f'docker image "{ref}" has no tag pinned (defaults to ":latest")'
        return [_make_finding(rule, server, detail)]
    tag = last_segment.rsplit(":", 1)[1]
    if _SEMVER_TAG.match(tag):
        return []
    detail = f'docker image "{ref}" uses floating tag ":{tag}", not a pinned version or digest'
    return [_make_finding(rule, server, detail)]


def _evaluate_npm_provenance(server: ServerConfig, rule: dict, detect: dict) -> list[Finding]:
    if "npx" not in server.command:
        return []
    pkg = extract_command_package(server)
    if not pkg:
        return []
    meta = _fetch_npm_metadata(pkg)
    if meta is None:
        # Network error or unknown package: no data to judge on, so no finding —
        # never let a provenance check fail closed against an offline/rate-limited registry.
        return []
    if "unpublished" in meta.get("time", {}):
        # npm's tombstone record for a fully unpublished package: no "dist-tags"/
        # "versions", just a "time.unpublished" marker. Distinct from — and a
        # stronger signal than — a live package that simply never set "repository":
        # the server's own launch command now points at nothing.
        detail = f'npm package "{pkg}" has been unpublished/removed from the npm registry'
        return [_make_finding(rule, server, detail)]
    latest = meta.get("dist-tags", {}).get("latest")
    version_info = meta.get("versions", {}).get(latest, {}) if latest else {}
    repo = version_info.get("repository") or meta.get("repository")
    if repo:
        return []
    detail = f'npm package "{pkg}" has no repository field in its registry metadata'
    return [_make_finding(rule, server, detail)]


def evaluate(server: ServerConfig, rules: list[dict]) -> list[Finding]:
    findings: list[Finding] = []
    for rule in rules:
        if rule.get("phase", "static") != "static":
            continue
        detect = rule.get("detect") or {}
        detect_type = detect.get("type")
        if detect_type == "typosquat":
            rule_findings = _evaluate_typosquat(server, rule, detect)
        elif detect_type == "npm_provenance":
            rule_findings = _evaluate_npm_provenance(server, rule, detect)
        else:
            rule_findings = _evaluate_regex(server, rule, detect)
        if not rule_findings and detect.get("also") == "oci_pin":
            rule_findings = _evaluate_oci_pin(server, rule, detect)
        findings.extend(rule_findings)
    return findings

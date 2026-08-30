"""Shared typosquat detection logic: package-name extraction from a launch
command, and edit-distance matching against a bundled reference list of
known-legitimate MCP server package names. Used by MCP-STATIC-006 (the
per-server static rule, in engine.py) and registry/artifacts.py's cluster
export (a registry-wide view over the same comparison) so there is exactly
one implementation of "how close is this package name to a known one," not
two.
"""

from __future__ import annotations

import functools
from collections.abc import Iterable
from pathlib import Path

import yaml
from rapidfuzz.distance import Levenshtein

from ..models import ServerConfig

_DATA_DIR = Path(__file__).parent / "data"


@functools.lru_cache
def load_reference_list(filename: str) -> tuple[str, ...]:
    data = yaml.safe_load((_DATA_DIR / filename).read_text(encoding="utf-8"))
    return tuple(data) if isinstance(data, list) else ()


def _package_name(spec: str) -> str:
    """Strip a trailing "@version" (or "@latest") from an npm-style package
    spec, preserving a scoped package's own leading "@scope/" segment."""
    if spec.startswith("@"):
        slash = spec.find("/")
        if slash == -1:
            return spec
        at = spec.find("@", slash)
    else:
        at = spec.find("@")
    return spec[:at] if at != -1 else spec


def extract_command_package(server: ServerConfig) -> str | None:
    """Find the npx/uvx-launched package name in a server's command tokens,
    version-stripped. Returns None for any other launcher shape (docker,
    cargo, dotnet, a bundle, or a remote URL) — those aren't npm/pypi
    package names and can't be compared to the reference list."""
    tokens = server.command
    for i, tok in enumerate(tokens):
        if tok in ("npx", "uvx"):
            for cand in tokens[i + 1 :]:
                if cand.startswith("-"):
                    continue
                return _package_name(cand)
    return None


def nearest_match(
    pkg: str, reference: tuple[str, ...], max_distance: int
) -> tuple[str, int] | None:
    """The closest reference name to `pkg`, if it's a near-miss (distance in
    [1, max_distance]) rather than an exact match or too far to be a
    plausible typosquat. Returns None when there's nothing to flag."""
    if not reference or pkg in reference:
        return None
    best = min(reference, key=lambda ref: Levenshtein.distance(pkg, ref))
    distance = Levenshtein.distance(pkg, best)
    if distance == 0 or distance > max_distance:
        return None
    return best, distance


def neighbors_of(
    reference_name: str, packages: Iterable[str], max_distance: int
) -> list[tuple[str, int]]:
    """Every distinct package name within [1, max_distance] edits of
    `reference_name` (an exact match is excluded — that's the legitimate
    package, not a lookalike), sorted by distance then name for a
    deterministic result."""
    matches: dict[str, int] = {}
    for pkg in packages:
        if pkg == reference_name:
            continue
        distance = Levenshtein.distance(pkg, reference_name)
        if 0 < distance <= max_distance:
            matches[pkg] = distance
    return sorted(matches.items(), key=lambda item: (item[1], item[0]))


def typosquat_rule_config(rules: list[dict]) -> tuple[str, int] | None:
    """Find the typosquat-type rule (MCP-STATIC-006 today) in a loaded rule
    set and return its (reference_list filename, max_distance), so the
    cluster export stays in sync with the rule's own YAML config instead of
    hardcoding a second copy of it. None if no such rule is loaded."""
    for rule in rules:
        detect = rule.get("detect") or {}
        if detect.get("type") == "typosquat":
            return detect.get("reference_list", ""), int(detect.get("max_distance", 2))
    return None

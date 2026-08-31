"""Load and enforce mcp-policy.yaml: which MCP servers/registries are
allowed, and which rule findings must not regress. Two independent checks
(check_allowlist/check_registries vs. check_findings) that cli.py's
`allowlist enforce` combines into one violation list — see
docs/policy.md and docs/superpowers/specs/2026-08-31-mcp-policy-allowlist-design.md
for why they're split this way.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal
from urllib.parse import urlparse

import yaml
from pydantic import BaseModel, Field, ValidationError, model_validator

from .models import SEVERITY_ORDER, Finding, PolicyViolation, ServerConfig
from .rules.engine import oci_image_ref
from .rules.typosquat import extract_command_package, extract_command_version


class PolicyError(Exception):
    """Raised for a malformed or invalid mcp-policy.yaml."""


class AllowedServer(BaseModel):
    name: str
    version: str | None = None
    digest: str | None = None

    @model_validator(mode="after")
    def _check_single_pin(self) -> AllowedServer:
        if self.version is not None and self.digest is not None:
            raise ValueError(f"server {self.name!r}: set either version or digest, not both")
        return self


class Policy(BaseModel):
    mode: Literal["baseline", "strict"] = "strict"
    fail_on: str = "medium"
    blocked_registries: list[str] = Field(default_factory=list)
    servers: list[AllowedServer] = Field(default_factory=list)

    @model_validator(mode="after")
    def _check_fail_on(self) -> Policy:
        if self.fail_on not in SEVERITY_ORDER:
            raise ValueError(
                f"fail_on must be one of {sorted(SEVERITY_ORDER)}, got {self.fail_on!r}"
            )
        return self


def load_policy(path: Path) -> Policy:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise PolicyError(f"malformed YAML in {path}: {exc}") from exc
    try:
        return Policy.model_validate(data)
    except ValidationError as exc:
        raise PolicyError(f"invalid policy in {path}: {exc}") from exc


def _oci_image_name(ref: str) -> str:
    """The image name portion of a docker image ref, with any tag or
    digest stripped — same tag-vs-registry-port disambiguation
    `rules/engine.py`'s oci_pin check already relies on."""
    if "@sha256:" in ref:
        return ref.split("@sha256:", 1)[0]
    last_segment = ref.rsplit("/", 1)[-1]
    if ":" in last_segment:
        return ref.rsplit(":", 1)[0]
    return ref


def server_identity(server: ServerConfig) -> str:
    """A server's identity for allowlist matching: npx/uvx package name,
    then a docker image name (tag/digest stripped), then an http server's
    URL host, falling back to the server's own config name (or its source
    path, if even that's empty) so no server is ever silently excluded
    from the allowlist check."""
    pkg = extract_command_package(server)
    if pkg:
        return pkg
    ref = oci_image_ref(server.command)
    if ref:
        return _oci_image_name(ref)
    if server.transport == "http" and server.url:
        host = urlparse(server.url).hostname
        if host:
            return host
    return server.name or server.source


def resolved_version(server: ServerConfig) -> str | None:
    """The version an npx/uvx-launched server currently resolves to, for
    comparison against an allowlist entry's declared `version` pin. None
    for any other launcher shape — those are compared via resolved_digest
    instead."""
    return extract_command_version(server)


def resolved_digest(server: ServerConfig) -> str | None:
    """The sha256 digest a docker-launched server currently resolves to,
    for comparison against an allowlist entry's declared `digest` pin.
    None if the server isn't a digest-referenced docker image."""
    ref = oci_image_ref(server.command)
    if ref and "@sha256:" in ref:
        return "sha256:" + ref.split("@sha256:", 1)[1]
    return None


def check_allowlist(servers: list[ServerConfig], policy: Policy) -> list[PolicyViolation]:
    violations: list[PolicyViolation] = []
    allowed = {entry.name: entry for entry in policy.servers}
    for server in servers:
        identity = server_identity(server)
        entry = allowed.get(identity)
        if entry is None:
            violations.append(
                PolicyViolation(
                    kind="unlisted_server",
                    server=identity,
                    severity="high",
                    detail=f'"{identity}" is not in the mcp-policy.yaml allowlist',
                )
            )
            continue
        if entry.version is not None and resolved_version(server) != entry.version:
            violations.append(
                PolicyViolation(
                    kind="version_drift",
                    server=identity,
                    severity="high",
                    detail=(
                        f'"{identity}" is pinned to version {entry.version!r} in the policy '
                        f"but resolves to {resolved_version(server)!r}"
                    ),
                )
            )
        if entry.digest is not None and resolved_digest(server) != entry.digest:
            violations.append(
                PolicyViolation(
                    kind="version_drift",
                    server=identity,
                    severity="high",
                    detail=(
                        f'"{identity}" is pinned to digest {entry.digest!r} in the policy '
                        f"but resolves to {resolved_digest(server)!r}"
                    ),
                )
            )
    return violations


def check_registries(servers: list[ServerConfig], policy: Policy) -> list[PolicyViolation]:
    violations: list[PolicyViolation] = []
    for server in servers:
        haystacks = [" ".join(server.command), server.url or ""]
        for blocked in policy.blocked_registries:
            if any(blocked in haystack for haystack in haystacks):
                identity = server_identity(server)
                violations.append(
                    PolicyViolation(
                        kind="blocked_registry",
                        server=identity,
                        severity="critical",
                        detail=f'"{identity}" references blocked registry "{blocked}"',
                    )
                )
                break
    return violations


def fingerprint(finding: Finding) -> str:
    """A stable identity for "this same finding" across scans, used to
    tell a pre-existing finding apart from a new one in baseline mode.
    Known limitation: renaming a server or changing its launch command
    changes `location`/`server` and so produces a "new" fingerprint even
    if nothing security-relevant changed — same trade-off any
    location-based baseline (e.g. an import-path baseline in a linter)
    makes; acceptable given issue #5's actual ask."""
    return f"{finding.rule_id}::{finding.server}::{finding.location}"


def load_baseline(path: Path) -> set[str]:
    if not path.exists():
        return set()
    return set(json.loads(path.read_text(encoding="utf-8")))


def write_baseline(path: Path, findings: list[Finding]) -> None:
    fingerprints = sorted({fingerprint(f) for f in findings})
    path.write_text(json.dumps(fingerprints, indent=2) + "\n", encoding="utf-8")


def check_findings(
    findings: list[Finding], policy: Policy, baseline: set[str]
) -> list[PolicyViolation]:
    violations: list[PolicyViolation] = []
    for f in findings:
        if policy.mode == "baseline" and fingerprint(f) in baseline:
            continue
        if SEVERITY_ORDER[f.severity] >= SEVERITY_ORDER[policy.fail_on]:
            violations.append(
                PolicyViolation(
                    kind="finding",
                    server=f.server,
                    rule_id=f.rule_id,
                    severity=f.severity,
                    detail=f.title,
                )
            )
    return violations


def render_markdown(
    violations: list[PolicyViolation], server_count: int, policy_path: Path
) -> str:
    lines = [
        "## mcphound allowlist check",
        "",
        f"Checked {server_count} server(s) against `{policy_path}`.",
        "",
    ]
    if not violations:
        lines.append("No violations.")
        return "\n".join(lines) + "\n"
    lines.append(f"**{len(violations)} violation(s):**")
    lines.append("")
    lines.append("| Kind | Server | Detail |")
    lines.append("|---|---|---|")
    for v in violations:
        server = f"`{v.server}`" if v.server else "-"
        lines.append(f"| {v.kind} | {server} | {v.detail} |")
    return "\n".join(lines) + "\n"

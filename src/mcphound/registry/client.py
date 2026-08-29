"""HTTP client for the official MCP Registry (https://registry.modelcontextprotocol.io).

PARSING ONLY — never executes a discovered server. The registry has no delta/
webhook mechanism, so a full page-through is required on every poll; see
docs/superpowers/specs/2026-08-29-registry-poller-design.md.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any

import httpx

DEFAULT_PAGE_LIMIT = 100
_TIMEOUT = 15.0


@dataclass
class RegistryPackage:
    registry_type: str
    identifier: str
    version: str
    transport: str | None
    file_sha256: str | None
    runtime_arguments: Any
    package_arguments: Any
    environment_variables: Any
    raw: dict


@dataclass
class RegistryRemote:
    url: str
    transport: str | None
    raw: dict


@dataclass
class RegistryServerEntry:
    name: str
    version: str
    title: str | None
    description: str | None
    website_url: str | None
    repository_url: str | None
    repository_source: str | None
    is_latest: bool
    status: str | None
    published_at: str | None
    packages: list[RegistryPackage] = field(default_factory=list)
    remotes: list[RegistryRemote] = field(default_factory=list)
    raw: dict = field(default_factory=dict)


def _fetch_page(base_url: str, cursor: str | None, limit: int) -> dict:
    """Isolated so tests can monkeypatch it instead of hitting the real registry."""
    params: dict[str, Any] = {"limit": limit}
    if cursor:
        params["cursor"] = cursor
    resp = httpx.get(f"{base_url.rstrip('/')}/v0.1/servers", params=params, timeout=_TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def _parse_package(pkg: dict) -> RegistryPackage:
    return RegistryPackage(
        registry_type=pkg.get("registryType", ""),
        identifier=pkg.get("identifier", ""),
        version=pkg.get("version", ""),
        transport=pkg.get("transport"),
        file_sha256=pkg.get("fileSha256"),
        runtime_arguments=pkg.get("runtimeArguments"),
        package_arguments=pkg.get("packageArguments"),
        environment_variables=pkg.get("environmentVariables"),
        raw=pkg,
    )


def _parse_remote(remote: dict) -> RegistryRemote:
    return RegistryRemote(
        url=remote.get("url", ""),
        transport=remote.get("type") or remote.get("transport"),
        raw=remote,
    )


def _parse_entry(entry: dict) -> RegistryServerEntry:
    meta = (entry.get("_meta") or {}).get("io.modelcontextprotocol.registry/official") or {}
    repository = entry.get("repository") or {}
    return RegistryServerEntry(
        name=entry.get("name", ""),
        version=entry.get("version", ""),
        title=entry.get("title"),
        description=entry.get("description"),
        website_url=entry.get("websiteUrl"),
        repository_url=repository.get("url"),
        repository_source=repository.get("source"),
        is_latest=bool(meta.get("isLatest", False)),
        status=meta.get("status"),
        published_at=meta.get("publishedAt"),
        packages=[_parse_package(p) for p in entry.get("packages") or []],
        remotes=[_parse_remote(r) for r in entry.get("remotes") or []],
        raw=entry,
    )


def iter_servers(
    base_url: str, page_limit: int = DEFAULT_PAGE_LIMIT
) -> Iterator[RegistryServerEntry]:
    """Page through the full registry, yielding one parsed entry at a time.

    No delta/webhook exists on this API — every call walks the entire registry.
    """
    cursor: str | None = None
    while True:
        page = _fetch_page(base_url, cursor, page_limit)
        for entry in page.get("servers", []):
            yield _parse_entry(entry)
        cursor = (page.get("metadata") or {}).get("nextCursor") or None
        if not cursor:
            break

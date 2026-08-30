"""HTTP client for the official MCP Registry (https://registry.modelcontextprotocol.io).

PARSING ONLY — never executes a discovered server. The registry has no delta/
webhook mechanism, so a full page-through is required on every poll; see
docs/registry-poller.md.
"""

from __future__ import annotations

import time
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any

import httpx

DEFAULT_PAGE_LIMIT = 100
_TIMEOUT = 15.0
_MAX_ATTEMPTS = 5
_RETRY_BACKOFF_SECONDS = 2.0


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
    """Isolated so tests can monkeypatch it instead of hitting the real registry.

    `version=latest` filters the response to one entry per server (the current
    version) instead of every version ever published — the full-history walk
    was pulling ~3x the entry count for rows `registry-scan` never looks at
    (it only scans `is_latest=True` versions). Confirmed against the live
    OpenAPI spec (https://registry.modelcontextprotocol.io/openapi.yaml).

    Retries transient network/server errors with backoff: a full poll makes
    hundreds of sequential page requests (~25k servers / page_limit), so a
    single isolated timeout otherwise loses 30+ minutes of prior progress —
    this bit a real nightly CI run (2026-08-30) via httpx.ReadTimeout on one
    page deep into the walk. Client errors (4xx) aren't retried — retrying a
    bad request forever would just waste the backoff budget.
    """
    params: dict[str, Any] = {"limit": limit, "version": "latest"}
    if cursor:
        params["cursor"] = cursor
    url = f"{base_url.rstrip('/')}/v0.1/servers"

    last_exc: Exception = RuntimeError("unreachable")
    for attempt in range(_MAX_ATTEMPTS):
        try:
            resp = httpx.get(url, params=params, timeout=_TIMEOUT)
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code < 500:
                raise
            last_exc = exc
        except (httpx.TimeoutException, httpx.TransportError) as exc:
            last_exc = exc
        if attempt < _MAX_ATTEMPTS - 1:
            time.sleep(_RETRY_BACKOFF_SECONDS * (2**attempt))
    raise last_exc


def _parse_transport(transport: Any) -> str | None:
    """Unwrap the registry's transport shape into a bare string.

    Real API: `packages[].transport` is an object (e.g. `{"type": "stdio"}`),
    an anyOf of StdioTransport/StreamableHttpTransport/SseTransport in the
    official schema. Stay defensive in case some entries carry a bare string.
    """
    if isinstance(transport, dict):
        return transport.get("type")
    return transport


def _parse_package(pkg: dict) -> RegistryPackage:
    return RegistryPackage(
        registry_type=pkg.get("registryType", ""),
        identifier=pkg.get("identifier", ""),
        version=pkg.get("version", ""),
        transport=_parse_transport(pkg.get("transport")),
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
    server = entry.get("server") or {}
    repository = server.get("repository") or {}
    return RegistryServerEntry(
        name=server.get("name", ""),
        version=server.get("version", ""),
        title=server.get("title"),
        description=server.get("description"),
        website_url=server.get("websiteUrl"),
        repository_url=repository.get("url"),
        repository_source=repository.get("source"),
        is_latest=bool(meta.get("isLatest", False)),
        status=meta.get("status"),
        published_at=meta.get("publishedAt"),
        packages=[_parse_package(p) for p in server.get("packages") or []],
        remotes=[_parse_remote(r) for r in server.get("remotes") or []],
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

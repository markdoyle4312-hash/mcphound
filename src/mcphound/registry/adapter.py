"""Adapter: turn a registry Version row into a ServerConfig the existing
rule engine can evaluate, without ever executing anything.

A registry entry doesn't carry a literal launch command the way a client
config file does — this module synthesizes the command a real client would
run, per `registry_type`, from the row's runtime_arguments/package_arguments/
environment_variables jsonb columns. `cargo`/`nuget`/`mcpb` launchers are a
best-effort guess (the registry schema doesn't prescribe one); revisit once
real registry data of these types is observed.

For `npm`/`pypi`, the identifier is pinned to this row's exact version
(`pkg@1.2.3`) — a Version row IS a specific pinned release, and
MCP-STATIC-004 ("unpinned or @latest package") would otherwise fire on
every single npm/pypi server in the registry, since a bare package name
with no `@version` looks exactly like an unpinned launch to that rule.
"""

from __future__ import annotations

from typing import Any

from ..db.models import Version
from ..models import ServerConfig

_LAUNCHERS: dict[str, list[str]] = {
    "npm": ["npx", "-y"],
    "pypi": ["uvx"],
    "oci": ["docker", "run"],
    "cargo": ["cargo", "run", "--"],
    "nuget": ["dotnet", "tool", "run"],
    "mcpb": [],
}

_VERSION_PINNED_TYPES = {"npm", "pypi"}

_HTTP_TRANSPORTS = ("http", "sse", "streamable-http")


def _argument_tokens(arguments: Any) -> list[str]:
    """Best-effort flatten of the registry's packageArguments/runtimeArguments
    shape into command tokens. Accepts a list of plain strings, or a list of
    {"name": ..., "value": ...} / {"value": ...} argument objects; anything
    else (None, a dict, an unrecognized shape) yields no tokens rather than
    guessing wrong."""
    if not isinstance(arguments, list):
        return []
    tokens: list[str] = []
    for arg in arguments:
        if isinstance(arg, str):
            tokens.append(arg)
        elif isinstance(arg, dict):
            name = arg.get("name")
            value = arg.get("value")
            if name:
                tokens.append(str(name))
            if value is not None:
                tokens.append(str(value))
    return tokens


def _env(environment_variables: Any) -> dict[str, str]:
    if isinstance(environment_variables, dict):
        return {str(k): str(v) for k, v in environment_variables.items()}
    if isinstance(environment_variables, list):
        env: dict[str, str] = {}
        for entry in environment_variables:
            if isinstance(entry, dict) and entry.get("name"):
                env[str(entry["name"])] = str(entry.get("value", ""))
        return env
    return {}


def version_to_server_config(version: Version) -> ServerConfig:
    """Synthesize the ServerConfig the rule engine would see if this version
    were installed and launched. PARSING/SYNTHESIS ONLY — never executes
    anything; the result is only ever passed to rules.engine.evaluate(),
    which does pure text matching."""
    server_name = version.server.name
    source = f"registry:{server_name}@{version.version}"

    if version.registry_type == "remote":
        return ServerConfig(
            name=server_name,
            transport="http",
            command=[],
            url=version.identifier,
            env={},
            source=source,
            raw=version.raw_json,
        )

    identifier = version.identifier
    if version.registry_type in _VERSION_PINNED_TYPES and version.version:
        identifier = f"{identifier}@{version.version}"

    launcher = _LAUNCHERS.get(version.registry_type, [])
    tokens = _argument_tokens(version.runtime_arguments) + _argument_tokens(
        version.package_arguments
    )
    command = [*launcher, identifier, *tokens]
    transport = "http" if version.transport in _HTTP_TRANSPORTS else "stdio"

    return ServerConfig(
        name=server_name,
        transport=transport,
        command=command,
        url=None,
        env=_env(version.environment_variables),
        source=source,
        raw=version.raw_json,
    )

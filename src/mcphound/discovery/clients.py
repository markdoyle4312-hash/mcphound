"""Discover and parse MCP client configurations.

Supports the config shapes used by Claude Desktop / Claude Code (.mcp.json, ~/.claude.json),
Cursor, Windsurf, Gemini CLI, and OpenCode (opencode.json/jsonc, which uses the "mcp" key
and "local"/"remote" type names).

PARSING ONLY — this module never executes a server.
"""

from __future__ import annotations

import json
import os
import platform
import shlex
from pathlib import Path

from ..models import ServerConfig

HOME = Path.home()


def _user_config_paths() -> list[Path]:
    paths = [
        HOME / ".claude.json",
        HOME / ".mcp.json",
        HOME / ".cursor" / "mcp.json",
        HOME / ".codeium" / "windsurf" / "mcp_config.json",
        HOME / ".gemini" / "mcp.json",
        HOME / ".config" / "opencode" / "opencode.json",
    ]
    if platform.system() == "Darwin":
        paths.append(HOME / "Library/Application Support/Claude/claude_desktop_config.json")
    elif platform.system() == "Windows":
        appdata = os.environ.get("APPDATA", "")
        if appdata:
            paths.append(Path(appdata) / "Claude" / "claude_desktop_config.json")
    return paths


def _project_local_paths() -> list[Path]:
    return [
        Path.cwd() / ".mcp.json",
        Path.cwd() / "opencode.json",
        Path.cwd() / "opencode.jsonc",
    ]


def discover_configs(project_only: bool = False) -> list[Path]:
    """Project configs first, then user-level configs (skipped if `project_only`);
    only existing files."""
    candidates = _project_local_paths()
    if not project_only:
        candidates += _user_config_paths()
    return [p for p in candidates if p.exists()]


def _strip_jsonc(text: str) -> str:
    """Remove // and /* */ comments from JSONC, preserving string contents."""
    out = []
    i = 0
    n = len(text)
    in_string = False
    escape = False
    while i < n:
        ch = text[i]
        if in_string:
            out.append(ch)
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            i += 1
            continue
        # not in string
        if ch == '"':
            in_string = True
            out.append(ch)
            i += 1
            continue
        if ch == "/" and i + 1 < n:
            nxt = text[i + 1]
            if nxt == "/":
                while i < n and text[i] != "\n":
                    i += 1
                continue
            if nxt == "*":
                i += 2
                while i + 1 < n and not (text[i] == "*" and text[i + 1] == "/"):
                    i += 1
                i += 2
                continue
        out.append(ch)
        i += 1
    return "".join(out)


def _strip_trailing_commas(text: str) -> str:
    """Remove trailing commas before } or ] (JSONC/JSON5 allows them; json.loads doesn't)."""
    out = []
    i = 0
    n = len(text)
    in_string = False
    escape = False
    while i < n:
        ch = text[i]
        if in_string:
            out.append(ch)
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            i += 1
            continue
        if ch == '"':
            in_string = True
            out.append(ch)
            i += 1
            continue
        if ch == ",":
            j = i + 1
            while j < n and text[j] in " \t\r\n":
                j += 1
            if j < n and text[j] in "}]":
                i += 1
                continue
        out.append(ch)
        i += 1
    return "".join(out)


def _as_command_list(entry: dict) -> list[str]:
    cmd = entry.get("command")
    args = [str(a) for a in entry.get("args", [])]
    if isinstance(cmd, list):
        return [str(x) for x in cmd] + args
    if isinstance(cmd, str):
        parts = shlex.split(cmd)
        parts.extend(args)
        return parts
    return args


def load_servers(path: Path) -> list[ServerConfig]:
    text = path.read_text(encoding="utf-8")
    if path.suffix == ".jsonc":
        text = _strip_jsonc(text)
        text = _strip_trailing_commas(text)
    data = json.loads(text)

    raw_servers = data.get("mcpServers") or data.get("mcp") or {}
    servers: list[ServerConfig] = []
    for name, entry in raw_servers.items():
        if not isinstance(entry, dict) or entry.get("enabled") is False:
            continue
        raw_type = entry.get("type", "http" if entry.get("url") else "stdio")
        transport = "http" if raw_type in ("http", "remote", "sse", "streamable-http") else "stdio"
        env = entry.get("env") or entry.get("environment") or {}
        servers.append(
            ServerConfig(
                name=name,
                transport=transport,
                command=_as_command_list(entry),
                url=entry.get("url"),
                env={str(k): str(v) for k, v in env.items()},
                source=str(path),
                raw=entry,
            )
        )
    return servers

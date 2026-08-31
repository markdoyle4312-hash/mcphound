"""Core data models."""

from __future__ import annotations

from pydantic import BaseModel, Field

SEVERITIES = ("low", "medium", "high", "critical")
SEVERITY_ORDER = {"low": 1, "medium": 2, "high": 3, "critical": 4}


class ServerConfig(BaseModel):
    """One MCP server entry parsed from a client config file."""

    name: str
    transport: str = "stdio"  # "stdio" | "http"
    command: list[str] = Field(default_factory=list)
    url: str | None = None
    env: dict[str, str] = Field(default_factory=dict)
    source: str = ""  # config file path it came from
    raw: dict = Field(default_factory=dict)


class Finding(BaseModel):
    rule_id: str
    title: str
    severity: str
    confidence: str = "medium"
    owasp: str = ""  # LLMxx (OWASP LLM Top 10) or ASTxx (Agentic/MCP Top 10)
    phase: str = "static"  # static | dynamic
    server: str | None = None
    location: str = ""
    detail: str = ""
    recommendation: str = ""


class PolicyViolation(BaseModel):
    """One mcp-policy.yaml enforcement failure. `kind` is one of
    "unlisted_server", "version_drift", "blocked_registry", or "finding" —
    see docs/policy.md for what each means."""

    kind: str
    server: str | None = None
    rule_id: str | None = None
    severity: str
    detail: str = ""


class ScanResult(BaseModel):
    targets: list[str] = Field(default_factory=list)
    servers: list[ServerConfig] = Field(default_factory=list)
    findings: list[Finding] = Field(default_factory=list)

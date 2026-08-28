"""mcpvet CLI — scan and inspect MCP configurations without executing servers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer

from .discovery.clients import discover_configs, load_servers
from .models import SEVERITY_ORDER, ScanResult
from .output import to_json, to_sarif
from .rules.engine import evaluate
from .rules.loader import load_rules

app = typer.Typer(
    add_completion=False,
    help="mcpvet — security scanner for MCP servers and agent skills.",
)


def _collect(paths: list[Path] | None, deep: bool = False) -> ScanResult:
    config_paths = paths or discover_configs()
    servers = []
    for p in config_paths:
        if p.exists():
            servers.extend(load_servers(p))
    rules = load_rules()
    if not deep:
        rules = [r for r in rules if not r.get("network")]
    findings = []
    for server in servers:
        findings.extend(evaluate(server, rules))
    return ScanResult(
        targets=[str(p) for p in config_paths],
        servers=servers,
        findings=findings,
    )


@app.command()
def inspect(
    config: Annotated[
        Path | None, typer.Argument(help="Config file; defaults to auto-discovery")
    ] = None,
):
    """List configured MCP servers WITHOUT executing them."""
    paths = [config] if config else discover_configs()
    existing = [p for p in paths if p.exists()]
    if not existing:
        typer.echo("No MCP configurations found.")
        raise typer.Exit(0)
    for p in existing:
        typer.echo(f"\n# {p}")
        for s in load_servers(p):
            detail = s.url if s.transport == "http" else " ".join(s.command)
            typer.echo(f"  {s.name:<20} {s.transport:<6} {detail}")


@app.command()
def scan(
    config: Annotated[
        list[Path] | None, typer.Argument(help="Config file(s); defaults to auto-discovery")
    ] = None,
    as_json: Annotated[bool, typer.Option("--json", help="Machine-readable JSON output")] = False,
    sarif: Annotated[
        bool, typer.Option("--sarif", help="SARIF 2.1.0 output for code scanning")
    ] = False,
    fail_on: Annotated[
        str | None,
        typer.Option("--fail-on", help="Exit 1 on finding >= severity (low|medium|high|critical)"),
    ] = None,
    deep: Annotated[
        bool,
        typer.Option(
            "--deep",
            help="Also run network-dependent checks (e.g. npm registry provenance). "
            "Slower and not fully deterministic offline; off by default.",
        ),
    ] = False,
):
    """Scan MCP configurations for security issues (static analysis only)."""
    result = _collect(config, deep=deep)

    if sarif:
        typer.echo(json.dumps(to_sarif(result), indent=2))
    elif as_json:
        typer.echo(to_json(result))
    else:
        typer.echo(f"Scanned {len(result.servers)} server(s) from {len(result.targets)} config(s).")
        for f in result.findings:
            typer.echo(
                f"  [{f.severity.upper():<8}] {f.rule_id:<16} {f.server or '-':<16} {f.title}"
            )
        if not result.findings:
            typer.echo("  No findings.")

    if fail_on and fail_on in SEVERITY_ORDER:
        if any(SEVERITY_ORDER[f.severity] >= SEVERITY_ORDER[fail_on] for f in result.findings):
            raise typer.Exit(1)


if __name__ == "__main__":
    app()

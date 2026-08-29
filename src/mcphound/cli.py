"""mcphound CLI — scan and inspect MCP configurations without executing servers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated
from urllib.parse import quote

import typer

from . import __version__
from .discovery.clients import discover_configs, load_servers
from .models import SEVERITY_ORDER, ScanResult
from .output import to_json, to_sarif
from .rules.engine import evaluate
from .rules.loader import load_rules

app = typer.Typer(
    add_completion=False,
    help="mcphound — security scanner for MCP servers and agent skills.",
)

FEEDBACK_REPO = "markdoyle4312-hash/mcphound"


def _collect(
    paths: list[Path] | None, deep: bool = False, project_only: bool = False
) -> tuple[ScanResult, list[Path]]:
    explicit = paths is not None
    config_paths = paths or discover_configs(project_only=project_only)
    servers = []
    missing: list[Path] = []
    for p in config_paths:
        if p.exists():
            servers.extend(load_servers(p))
        elif explicit:
            missing.append(p)
    rules = load_rules()
    if not deep:
        rules = [r for r in rules if not r.get("network")]
    findings = []
    for server in servers:
        findings.extend(evaluate(server, rules))
    result = ScanResult(
        targets=[str(p) for p in config_paths],
        servers=servers,
        findings=findings,
    )
    return result, missing


@app.command()
def inspect(
    config: Annotated[
        Path | None, typer.Argument(help="Config file; defaults to auto-discovery")
    ] = None,
):
    """List configured MCP servers WITHOUT executing them."""
    if config is not None:
        if not config.exists():
            typer.echo(f"Warning: config file not found: {config}", err=True)
            raise typer.Exit(1)
        paths = [config]
    else:
        paths = discover_configs()
    if not paths:
        typer.echo("No MCP configurations found.")
        raise typer.Exit(0)
    for p in paths:
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
    self_: Annotated[
        bool,
        typer.Option(
            "--self",
            help="Only scan this project's own configs (.mcp.json, opencode.json[c] in "
            "the current directory) - skip user-level client configs. For CI/dogfood use "
            "where you want your repo's committed configs checked, not the machine's.",
        ),
    ] = False,
    output: Annotated[
        Path | None,
        typer.Option("-o", "--output", help="Write output to this file instead of stdout"),
    ] = None,
):
    """Scan MCP configurations for security issues (static analysis only)."""
    if self_ and config is not None:
        typer.echo("Error: --self can't be combined with explicit config file(s).", err=True)
        raise typer.Exit(2)
    result, missing = _collect(config, deep=deep, project_only=self_)

    for p in missing:
        typer.echo(f"Warning: config file not found: {p}", err=True)

    if sarif:
        text = json.dumps(to_sarif(result), indent=2)
    elif as_json:
        text = to_json(result)
    else:
        lines = [f"Scanned {len(result.servers)} server(s) from {len(result.targets)} config(s)."]
        for f in result.findings:
            lines.append(
                f"  [{f.severity.upper():<8}] {f.rule_id:<16} {f.server or '-':<16} {f.title}"
            )
        if not result.findings:
            lines.append("  No findings.")
        text = "\n".join(lines)

    if output:
        output.write_text(text + "\n", encoding="utf-8")
    else:
        typer.echo(text)

    severity_exceeded = fail_on and fail_on in SEVERITY_ORDER and any(
        SEVERITY_ORDER[f.severity] >= SEVERITY_ORDER[fail_on] for f in result.findings
    )
    if missing or severity_exceeded:
        raise typer.Exit(1)


@app.command()
def feedback(
    rule_id: Annotated[
        str,
        typer.Argument(help="Rule ID this finding is a false positive for, e.g. MCP-STATIC-004"),
    ],
    note: Annotated[
        str | None,
        typer.Option("--note", help="Why you believe this is a false positive"),
    ] = None,
):
    """Print a pre-filled GitHub issue URL for reporting a false positive.

    No network call and no GitHub auth — it only builds a URL for you to open.
    """
    rules = {r["id"]: r for r in load_rules()}
    rule = rules.get(rule_id)
    if rule is None:
        typer.echo(
            f"Error: unknown rule id {rule_id!r}. Known rules: {', '.join(sorted(rules))}",
            err=True,
        )
        raise typer.Exit(1)

    title = f"False positive: {rule_id} — {rule.get('title', '')}"
    body = "\n".join(
        [
            f"**Rule:** {rule_id} — {rule.get('title', '')}",
            f"**mcphound version:** {__version__}",
            "",
            "**Why this is a false positive:**",
            note or "<describe here>",
            "",
            "**Config snippet that triggered it** (redact secrets/tokens before pasting):",
            "```json",
            "",
            "```",
        ]
    )
    url = (
        f"https://github.com/{FEEDBACK_REPO}/issues/new"
        f"?title={quote(title)}&labels={quote('false-positive')}&body={quote(body)}"
    )
    typer.echo(f"Report a false positive for {rule_id}:\n\n{url}")


if __name__ == "__main__":
    app()

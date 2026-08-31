"""mcphound CLI — scan and inspect MCP configurations without executing servers."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Annotated
from urllib.parse import quote

import typer
import yaml

from . import __version__
from .discovery.clients import discover_configs, load_servers
from .models import SEVERITY_ORDER, ScanResult
from .output import to_json, to_sarif
from .policy import (
    PolicyError,
    check_allowlist,
    check_findings,
    check_registries,
    load_baseline,
    load_policy,
    render_markdown,
    resolved_digest,
    resolved_version,
    server_identity,
    write_baseline,
)
from .registry.config import load_config
from .rules.engine import evaluate
from .rules.loader import load_rules, rules_fingerprint

# `scan`/`inspect`/`feedback` must work with just the base install (no
# sqlalchemy/psycopg) — CHANGELOG.md: "kept out of the core install so
# `pip install mcphound` stays lightweight for scanner-only use". The
# registry-* commands need the `registry` extra, so their sqlalchemy-backed
# imports are guarded here rather than required at module scope; each
# registry-* command checks for None and raises a clear error instead of a
# raw ModuleNotFoundError traceback.
try:
    from .db.session import get_session_factory
    from .registry.artifacts import write_all_artifacts
    from .registry.poller import run_poll
    from .registry.scanner import DEFAULT_MAX_WORKERS, run_scan, run_scoring
except ImportError:
    get_session_factory = None
    write_all_artifacts = None
    run_poll = None
    run_scan = None
    run_scoring = None
    DEFAULT_MAX_WORKERS = 16


def _require_registry_extra() -> None:
    if get_session_factory is None:
        typer.echo(
            "Error: this command needs the 'registry' extra "
            "(pip install 'mcphound[registry]' / uv sync --extra registry).",
            err=True,
        )
        raise typer.Exit(1)


app = typer.Typer(
    add_completion=False,
    help="mcphound — security scanner for MCP servers and agent skills.",
)

FEEDBACK_REPO = "markdoyle4312-hash/mcphound"


def _enable_progress_logging() -> None:
    """registry-poll/registry-scan are long-running, network-bound batch jobs
    with no other console feedback — surface their INFO progress logs.
    Scoped to these commands only: `scan`/`inspect` must stay silent by
    default so --json/--sarif output stays deterministic (CLAUDE.md)."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")


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

    severity_exceeded = (
        fail_on
        and fail_on in SEVERITY_ORDER
        and any(SEVERITY_ORDER[f.severity] >= SEVERITY_ORDER[fail_on] for f in result.findings)
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


allowlist_app = typer.Typer(help="Manage and enforce an mcp-policy.yaml allowlist.")
app.add_typer(allowlist_app, name="allowlist")


@allowlist_app.command("init")
def allowlist_init(
    policy_path: Annotated[
        Path, typer.Option("--policy", help="Where to write the policy file")
    ] = Path("mcp-policy.yaml"),
    baseline_path: Annotated[
        Path, typer.Option("--baseline", help="Where to write the findings baseline")
    ] = Path("mcp-policy-baseline.json"),
    force: Annotated[
        bool, typer.Option("--force", help="Overwrite existing policy/baseline files")
    ] = False,
):
    """Bootstrap mcp-policy.yaml + a findings baseline from the current scan state."""
    if not force and (policy_path.exists() or baseline_path.exists()):
        typer.echo(
            f"Error: {policy_path} or {baseline_path} already exists. Use --force to overwrite.",
            err=True,
        )
        raise typer.Exit(1)
    result, _missing = _collect(None)
    servers_yaml = []
    for server in result.servers:
        identity = server_identity(server)
        entry: dict = {"name": identity}
        digest = resolved_digest(server)
        version = resolved_version(server)
        if digest:
            entry["digest"] = digest
        elif version:
            entry["version"] = version
        servers_yaml.append(entry)
    policy_data = {
        "mode": "baseline",
        "fail_on": "medium",
        "blocked_registries": [],
        "servers": servers_yaml,
    }
    policy_path.write_text(yaml.safe_dump(policy_data, sort_keys=False), encoding="utf-8")
    write_baseline(baseline_path, result.findings)
    typer.echo(
        f"Wrote {policy_path} ({len(servers_yaml)} server(s)) and {baseline_path} "
        f"({len(result.findings)} finding(s) baselined)."
    )


@allowlist_app.command("enforce")
def allowlist_enforce(
    config: Annotated[
        list[Path] | None, typer.Argument(help="Config file(s); defaults to auto-discovery")
    ] = None,
    policy_path: Annotated[
        Path, typer.Option("--policy", help="Path to the policy file")
    ] = Path("mcp-policy.yaml"),
    baseline_path: Annotated[
        Path, typer.Option("--baseline", help="Path to the findings baseline")
    ] = Path("mcp-policy-baseline.json"),
    as_json: Annotated[bool, typer.Option("--json", help="Machine-readable JSON output")] = False,
    markdown: Annotated[
        bool, typer.Option("--markdown", help="Markdown output (for PR comments)")
    ] = False,
    self_: Annotated[
        bool,
        typer.Option("--self", help="Only enforce against this project's own configs"),
    ] = False,
    deep: Annotated[
        bool, typer.Option("--deep", help="Also run network-dependent checks")
    ] = False,
    output: Annotated[
        Path | None,
        typer.Option("-o", "--output", help="Write output to this file instead of stdout"),
    ] = None,
):
    """Enforce mcp-policy.yaml against the current scan state."""
    if as_json and markdown:
        typer.echo("Error: --json and --markdown can't be combined.", err=True)
        raise typer.Exit(2)
    if self_ and config is not None:
        typer.echo("Error: --self can't be combined with explicit config file(s).", err=True)
        raise typer.Exit(2)
    if not policy_path.exists():
        typer.echo(
            f"Error: {policy_path} not found. Run `mcphound allowlist init` first.", err=True
        )
        raise typer.Exit(1)
    try:
        policy = load_policy(policy_path)
    except PolicyError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(1) from exc

    result, missing = _collect(config, deep=deep, project_only=self_)
    for p in missing:
        typer.echo(f"Warning: config file not found: {p}", err=True)

    baseline = load_baseline(baseline_path)
    violations = (
        check_allowlist(result.servers, policy)
        + check_registries(result.servers, policy)
        + check_findings(result.findings, policy, baseline)
    )

    if as_json:
        text = json.dumps([v.model_dump() for v in violations], indent=2)
    elif markdown:
        text = render_markdown(violations, len(result.servers), policy_path)
    else:
        lines = [f"Checked {len(result.servers)} server(s) against {policy_path}."]
        for v in violations:
            lines.append(f"  [{v.kind:<16}] {v.server or '-':<24} {v.detail}")
        if not violations:
            lines.append("  No violations.")
        text = "\n".join(lines)

    if output:
        output.write_text(text + "\n", encoding="utf-8")
    else:
        typer.echo(text)

    if missing or violations:
        raise typer.Exit(1)


@app.command(name="registry-poll")
def registry_poll(
    config_path: Annotated[
        Path, typer.Option("--config", help="Path to registry poll config YAML")
    ] = Path("config/registry.yaml"),
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Run the full pipeline but roll back instead of committing"),
    ] = False,
):
    """Poll the official MCP Registry and upsert servers/versions/hashes into Postgres."""
    _require_registry_extra()
    _enable_progress_logging()
    cfg = load_config(config_path)
    session = get_session_factory()()
    try:
        summary = run_poll(session, cfg.base_url, cfg.page_limit)
        if dry_run:
            session.rollback()
            typer.echo(f"[dry-run, rolled back] {summary.format()}")
        else:
            session.commit()
            typer.echo(summary.format())
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@app.command(name="registry-scan")
def registry_scan(
    config_path: Annotated[
        Path, typer.Option("--config", help="Path to registry poll config YAML")
    ] = Path("config/registry.yaml"),
    out: Annotated[
        Path | None,
        typer.Option(
            "--out",
            help="Directory for per-server JSON + index.json (default: config's artifacts_dir)",
        ),
    ] = None,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Run the full pipeline but roll back instead of committing"),
    ] = False,
    workers: Annotated[
        int,
        typer.Option(
            "--workers",
            help="Concurrent workers for rule evaluation (npm provenance is network-bound)",
        ),
    ] = DEFAULT_MAX_WORKERS,
):
    """Batch-scan every currently-listed registry server, score it 0-100, and
    write JSON artifacts. Run after `registry-poll` has populated the DB."""
    _require_registry_extra()
    _enable_progress_logging()
    cfg = load_config(config_path)
    rules = load_rules()
    # Staleness key for the incremental rescan: content-addressed on the rule
    # set, not __version__ — see rules_fingerprint()'s docstring for why.
    scan_fingerprint = rules_fingerprint(rules)
    out_dir = out or Path(cfg.artifacts_dir)
    session = get_session_factory()()
    try:
        scan_summary = run_scan(session, rules, scan_fingerprint, max_workers=workers)
        score_summary = run_scoring(session, scan_fingerprint)
        if dry_run:
            session.rollback()
            typer.echo(f"[dry-run, rolled back] {scan_summary.format()}; {score_summary.format()}")
        else:
            session.commit()
            written, clustered = write_all_artifacts(session, out_dir, rules)
            typer.echo(
                f"{scan_summary.format()}; {score_summary.format()}; "
                f"wrote artifacts for {written} server(s) and {clustered} typosquat "
                f"cluster(s) to {out_dir}"
            )
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@app.command(name="registry-export")
def registry_export(
    config_path: Annotated[
        Path, typer.Option("--config", help="Path to registry poll config YAML")
    ] = Path("config/registry.yaml"),
    out: Annotated[
        Path | None,
        typer.Option(
            "--out",
            help="Directory for per-server JSON + index.json (default: config's artifacts_dir)",
        ),
    ] = None,
):
    """Re-materialize JSON artifacts (per-server scores, leaderboard index,
    typosquat clusters) from already-scored DB state, without rescanning.
    Cheap enough to run before every site deploy; run `registry-scan` on
    its own schedule to actually update scores."""
    _require_registry_extra()
    cfg = load_config(config_path)
    rules = load_rules()
    out_dir = out or Path(cfg.artifacts_dir)
    session = get_session_factory()()
    try:
        written, clustered = write_all_artifacts(session, out_dir, rules)
        typer.echo(
            f"wrote artifacts for {written} server(s) and {clustered} typosquat "
            f"cluster(s) to {out_dir}"
        )
    finally:
        session.close()


if __name__ == "__main__":
    app()

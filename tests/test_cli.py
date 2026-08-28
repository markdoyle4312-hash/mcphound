import json
from pathlib import Path

from typer.testing import CliRunner

from mcpvet.cli import app

FIXTURES = Path(__file__).parent / "fixtures"


def test_inspect_lists_servers_without_executing():
    runner = CliRunner()
    result = runner.invoke(app, ["inspect", str(FIXTURES / "configs" / "claude_desktop.json")])
    assert result.exit_code == 0
    assert "claude-desktop-server" in result.stdout
    assert "stdio" in result.stdout


def test_inspect_skips_missing_config():
    runner = CliRunner()
    result = runner.invoke(app, ["inspect", str(FIXTURES / "configs" / "does_not_exist.json")])
    assert result.exit_code == 0
    assert "No MCP configurations found." in result.stdout


def _finding_rule_ids(stdout: str) -> set[str]:
    return {f["rule_id"] for f in json.loads(stdout)["findings"]}


def test_scan_excludes_network_rules_by_default(monkeypatch):
    from mcpvet.rules import engine

    monkeypatch.setattr(
        engine,
        "_fetch_npm_metadata",
        lambda pkg: {"dist-tags": {"latest": "1.0.0"}, "versions": {"1.0.0": {}}},
    )
    runner = CliRunner()
    cfg = FIXTURES / "static" / "MCP-STATIC-007" / "mcp-malicious.json"
    result = runner.invoke(app, ["scan", str(cfg), "--json"])
    assert result.exit_code == 0
    assert "MCP-STATIC-007" not in _finding_rule_ids(result.stdout)


def test_scan_deep_runs_network_rules(monkeypatch):
    from mcpvet.rules import engine

    monkeypatch.setattr(
        engine,
        "_fetch_npm_metadata",
        lambda pkg: {"dist-tags": {"latest": "1.0.0"}, "versions": {"1.0.0": {}}},
    )
    runner = CliRunner()
    cfg = FIXTURES / "static" / "MCP-STATIC-007" / "mcp-malicious.json"
    result = runner.invoke(app, ["scan", str(cfg), "--deep", "--json"])
    assert result.exit_code == 0
    assert "MCP-STATIC-007" in _finding_rule_ids(result.stdout)

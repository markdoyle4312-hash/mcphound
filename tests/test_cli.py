import json
from pathlib import Path
from unittest.mock import MagicMock

from typer.testing import CliRunner

from mcphound.cli import app

FIXTURES = Path(__file__).parent / "fixtures"


def test_inspect_lists_servers_without_executing():
    runner = CliRunner()
    result = runner.invoke(app, ["inspect", str(FIXTURES / "configs" / "claude_desktop.json")])
    assert result.exit_code == 0
    assert "claude-desktop-server" in result.stdout
    assert "stdio" in result.stdout


def test_inspect_errors_on_explicit_missing_config():
    runner = CliRunner()
    missing = FIXTURES / "configs" / "does_not_exist.json"
    result = runner.invoke(app, ["inspect", str(missing)])
    assert result.exit_code != 0
    assert "not found" in result.output
    assert str(missing) in result.output


def test_inspect_auto_discovery_finds_nothing_stays_silent(tmp_path, monkeypatch):
    from mcphound.discovery import clients as discovery_clients

    monkeypatch.setattr(discovery_clients, "HOME", tmp_path / "home")
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(app, ["inspect"])
    assert result.exit_code == 0
    assert "No MCP configurations found." in result.stdout


def test_scan_output_flag_writes_to_file(tmp_path):
    runner = CliRunner()
    out = tmp_path / "results.json"
    cfg = FIXTURES / "static" / "MCP-STATIC-001" / "mcp-malicious.json"
    result = runner.invoke(app, ["scan", str(cfg), "--json", "-o", str(out)])
    assert result.exit_code == 0
    assert result.stdout == ""
    data = json.loads(out.read_text())
    assert data["findings"]


def test_scan_errors_on_explicit_missing_config():
    runner = CliRunner()
    missing = FIXTURES / "configs" / "does_not_exist.json"
    result = runner.invoke(app, ["scan", str(missing)])
    assert result.exit_code != 0
    assert "not found" in result.output
    assert str(missing) in result.output


def test_scan_auto_discovery_finds_nothing_stays_silent(tmp_path, monkeypatch):
    from mcphound.discovery import clients as discovery_clients

    monkeypatch.setattr(discovery_clients, "HOME", tmp_path / "home")
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(app, ["scan"])
    assert result.exit_code == 0
    assert "No findings." in result.stdout


def _finding_rule_ids(stdout: str) -> set[str]:
    return {f["rule_id"] for f in json.loads(stdout)["findings"]}


def test_scan_excludes_network_rules_by_default(monkeypatch):
    from mcphound.rules import engine

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
    from mcphound.rules import engine

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


def test_scan_self_only_reads_project_local_configs(tmp_path, monkeypatch):
    from mcphound.discovery import clients as discovery_clients

    fake_home = tmp_path / "home"
    fake_home.mkdir()
    monkeypatch.setattr(discovery_clients, "HOME", fake_home)
    # A "user-level" config that --self must ignore, even though it exists.
    (fake_home / ".mcp.json").write_text('{"mcpServers": {}}', encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".mcp.json").write_text(
        (FIXTURES / "static" / "MCP-STATIC-001" / "mcp-malicious.json").read_text(
            encoding="utf-8"
        ),
        encoding="utf-8",
    )
    runner = CliRunner()
    result = runner.invoke(app, ["scan", "--self", "--json"])
    assert result.exit_code == 0
    assert "MCP-STATIC-001" in _finding_rule_ids(result.stdout)


def test_scan_self_rejects_explicit_config():
    runner = CliRunner()
    cfg = FIXTURES / "static" / "MCP-STATIC-001" / "mcp-malicious.json"
    result = runner.invoke(app, ["scan", "--self", str(cfg)])
    assert result.exit_code != 0
    assert "--self" in result.output


def test_feedback_prints_prefilled_github_issue_url():
    runner = CliRunner()
    result = runner.invoke(app, ["feedback", "MCP-STATIC-004", "--note", "pinned via lockfile"])
    assert result.exit_code == 0
    assert "github.com/markdoyle4312-hash/mcphound/issues/new" in result.stdout
    assert "MCP-STATIC-004" in result.stdout


def test_feedback_errors_on_unknown_rule_id():
    runner = CliRunner()
    result = runner.invoke(app, ["feedback", "MCP-STATIC-999"])
    assert result.exit_code != 0
    assert "unknown rule id" in result.output


def test_registry_poll_dry_run_rolls_back(monkeypatch, tmp_path):
    from mcphound import cli as cli_module

    cfg_path = tmp_path / "registry.yaml"
    cfg_path.write_text(
        "registry:\n  base_url: https://registry.example\n  page_limit: 5\n", encoding="utf-8"
    )

    fake_session = MagicMock()
    fake_summary = MagicMock()
    fake_summary.format.return_value = "servers: 0 seen"

    monkeypatch.setattr(cli_module, "get_session_factory", lambda: (lambda: fake_session))
    monkeypatch.setattr(cli_module, "run_poll", lambda session, base_url, page_limit: fake_summary)

    runner = CliRunner()
    result = runner.invoke(app, ["registry-poll", "--config", str(cfg_path), "--dry-run"])

    assert result.exit_code == 0
    fake_session.rollback.assert_called_once()
    fake_session.commit.assert_not_called()
    assert "dry-run" in result.stdout


def test_registry_poll_commits_by_default(monkeypatch, tmp_path):
    from mcphound import cli as cli_module

    cfg_path = tmp_path / "registry.yaml"
    cfg_path.write_text("registry:\n  base_url: https://registry.example\n", encoding="utf-8")

    fake_session = MagicMock()
    fake_summary = MagicMock()
    fake_summary.format.return_value = "servers: 1 seen"

    monkeypatch.setattr(cli_module, "get_session_factory", lambda: (lambda: fake_session))
    monkeypatch.setattr(cli_module, "run_poll", lambda session, base_url, page_limit: fake_summary)

    runner = CliRunner()
    result = runner.invoke(app, ["registry-poll", "--config", str(cfg_path)])

    assert result.exit_code == 0
    fake_session.commit.assert_called_once()
    fake_session.rollback.assert_not_called()
    assert "servers: 1 seen" in result.stdout

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
        (FIXTURES / "static" / "MCP-STATIC-001" / "mcp-malicious.json").read_text(encoding="utf-8"),
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

    monkeypatch.setattr(cli_module, "get_session_factory", lambda: lambda: fake_session)
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

    monkeypatch.setattr(cli_module, "get_session_factory", lambda: lambda: fake_session)
    monkeypatch.setattr(cli_module, "run_poll", lambda session, base_url, page_limit: fake_summary)

    runner = CliRunner()
    result = runner.invoke(app, ["registry-poll", "--config", str(cfg_path)])

    assert result.exit_code == 0
    fake_session.commit.assert_called_once()
    fake_session.rollback.assert_not_called()
    assert "servers: 1 seen" in result.stdout


def test_registry_scan_dry_run_rolls_back_and_skips_artifacts(monkeypatch, tmp_path):
    from mcphound import cli as cli_module

    cfg_path = tmp_path / "registry.yaml"
    cfg_path.write_text("registry:\n  base_url: https://registry.example\n", encoding="utf-8")

    fake_session = MagicMock()
    fake_scan_summary = MagicMock()
    fake_scan_summary.format.return_value = "versions: 0 in scope"
    fake_score_summary = MagicMock()
    fake_score_summary.format.return_value = "servers scored: 0"
    write_all_artifacts_mock = MagicMock()

    monkeypatch.setattr(cli_module, "get_session_factory", lambda: lambda: fake_session)
    monkeypatch.setattr(
        cli_module, "run_scan", lambda session, rules, version, max_workers: fake_scan_summary
    )
    monkeypatch.setattr(cli_module, "run_scoring", lambda session, version: fake_score_summary)
    monkeypatch.setattr(cli_module, "write_all_artifacts", write_all_artifacts_mock)

    runner = CliRunner()
    result = runner.invoke(app, ["registry-scan", "--config", str(cfg_path), "--dry-run"])

    assert result.exit_code == 0
    fake_session.rollback.assert_called_once()
    fake_session.commit.assert_not_called()
    write_all_artifacts_mock.assert_not_called()
    assert "dry-run" in result.stdout


def test_registry_scan_commits_and_writes_artifacts_by_default(monkeypatch, tmp_path):
    from mcphound import cli as cli_module

    cfg_path = tmp_path / "registry.yaml"
    cfg_path.write_text("registry:\n  base_url: https://registry.example\n", encoding="utf-8")
    out_dir = tmp_path / "artifacts"

    fake_session = MagicMock()
    fake_scan_summary = MagicMock()
    fake_scan_summary.format.return_value = "versions: 1 in scope"
    fake_score_summary = MagicMock()
    fake_score_summary.format.return_value = "servers scored: 1"

    monkeypatch.setattr(cli_module, "get_session_factory", lambda: lambda: fake_session)
    monkeypatch.setattr(
        cli_module, "run_scan", lambda session, rules, version, max_workers: fake_scan_summary
    )
    monkeypatch.setattr(cli_module, "run_scoring", lambda session, version: fake_score_summary)
    monkeypatch.setattr(cli_module, "write_all_artifacts", lambda session, out, rules: (1, 0))

    runner = CliRunner()
    result = runner.invoke(app, ["registry-scan", "--config", str(cfg_path), "--out", str(out_dir)])

    assert result.exit_code == 0
    fake_session.commit.assert_called_once()
    fake_session.rollback.assert_not_called()
    assert "servers scored: 1" in result.stdout
    assert "wrote artifacts for 1 server" in result.stdout


def test_registry_scan_passes_workers_flag_to_run_scan(monkeypatch, tmp_path):
    from mcphound import cli as cli_module

    cfg_path = tmp_path / "registry.yaml"
    cfg_path.write_text("registry:\n  base_url: https://registry.example\n", encoding="utf-8")

    fake_session = MagicMock()
    fake_scan_summary = MagicMock()
    fake_scan_summary.format.return_value = "versions: 0 in scope"
    fake_score_summary = MagicMock()
    fake_score_summary.format.return_value = "servers scored: 0"
    run_scan_mock = MagicMock(return_value=fake_scan_summary)

    monkeypatch.setattr(cli_module, "get_session_factory", lambda: lambda: fake_session)
    monkeypatch.setattr(cli_module, "run_scan", run_scan_mock)
    monkeypatch.setattr(cli_module, "run_scoring", lambda session, version: fake_score_summary)
    monkeypatch.setattr(cli_module, "write_all_artifacts", lambda session, out, rules: (0, 0))

    runner = CliRunner()
    result = runner.invoke(app, ["registry-scan", "--config", str(cfg_path), "--workers", "5"])

    assert result.exit_code == 0
    assert run_scan_mock.call_args.kwargs["max_workers"] == 5


def test_registry_scan_defaults_out_dir_from_config(monkeypatch, tmp_path):
    from mcphound import cli as cli_module

    cfg_path = tmp_path / "registry.yaml"
    cfg_path.write_text(
        "registry:\n  base_url: https://registry.example\n  artifacts_dir: my-artifacts\n",
        encoding="utf-8",
    )

    fake_session = MagicMock()
    fake_scan_summary = MagicMock()
    fake_scan_summary.format.return_value = "versions: 0 in scope"
    fake_score_summary = MagicMock()
    fake_score_summary.format.return_value = "servers scored: 0"
    write_all_artifacts_mock = MagicMock(return_value=(0, 0))

    monkeypatch.setattr(cli_module, "get_session_factory", lambda: lambda: fake_session)
    monkeypatch.setattr(
        cli_module, "run_scan", lambda session, rules, version, max_workers: fake_scan_summary
    )
    monkeypatch.setattr(cli_module, "run_scoring", lambda session, version: fake_score_summary)
    monkeypatch.setattr(cli_module, "write_all_artifacts", write_all_artifacts_mock)

    runner = CliRunner()
    result = runner.invoke(app, ["registry-scan", "--config", str(cfg_path)])

    assert result.exit_code == 0
    called_out_dir = write_all_artifacts_mock.call_args.args[1]
    assert str(called_out_dir) == "my-artifacts"


def test_registry_export_writes_artifacts_without_scanning(monkeypatch, tmp_path):
    from mcphound import cli as cli_module

    cfg_path = tmp_path / "registry.yaml"
    cfg_path.write_text("registry:\n  base_url: https://registry.example\n", encoding="utf-8")
    out_dir = tmp_path / "out"

    fake_session = MagicMock()
    write_all_artifacts_mock = MagicMock(return_value=(3, 1))
    run_scan_mock = MagicMock()

    monkeypatch.setattr(cli_module, "get_session_factory", lambda: lambda: fake_session)
    monkeypatch.setattr(cli_module, "write_all_artifacts", write_all_artifacts_mock)
    monkeypatch.setattr(cli_module, "run_scan", run_scan_mock)

    runner = CliRunner()
    result = runner.invoke(
        app, ["registry-export", "--config", str(cfg_path), "--out", str(out_dir)]
    )

    assert result.exit_code == 0
    run_scan_mock.assert_not_called()
    fake_session.commit.assert_not_called()
    called_out_dir = write_all_artifacts_mock.call_args.args[1]
    assert called_out_dir == out_dir
    assert "wrote artifacts for 3 server(s) and 1 typosquat cluster(s)" in result.stdout


def test_allowlist_init_writes_policy_and_baseline(tmp_path, monkeypatch):
    from mcphound.discovery import clients as discovery_clients

    fake_home = tmp_path / "home"
    fake_home.mkdir()
    monkeypatch.setattr(discovery_clients, "HOME", fake_home)
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".mcp.json").write_text(
        (FIXTURES / "static" / "MCP-STATIC-001" / "mcp-malicious.json").read_text(
            encoding="utf-8"
        ),
        encoding="utf-8",
    )
    runner = CliRunner()
    result = runner.invoke(app, ["allowlist", "init"])
    assert result.exit_code == 0
    assert (tmp_path / "mcp-policy.yaml").exists()
    assert (tmp_path / "mcp-policy-baseline.json").exists()


def test_allowlist_init_refuses_to_overwrite_without_force(tmp_path, monkeypatch):
    from mcphound.discovery import clients as discovery_clients

    fake_home = tmp_path / "home"
    fake_home.mkdir()
    monkeypatch.setattr(discovery_clients, "HOME", fake_home)
    monkeypatch.chdir(tmp_path)
    (tmp_path / "mcp-policy.yaml").write_text("mode: strict\n", encoding="utf-8")
    runner = CliRunner()
    result = runner.invoke(app, ["allowlist", "init"])
    assert result.exit_code == 1
    assert "--force" in result.output


def test_allowlist_enforce_errors_when_policy_missing(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(app, ["allowlist", "enforce"])
    assert result.exit_code == 1
    assert "allowlist init" in result.output


def test_allowlist_init_then_enforce_round_trips_clean(tmp_path, monkeypatch):
    from mcphound.discovery import clients as discovery_clients

    fake_home = tmp_path / "home"
    fake_home.mkdir()
    monkeypatch.setattr(discovery_clients, "HOME", fake_home)
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".mcp.json").write_text(
        (FIXTURES / "static" / "MCP-STATIC-001" / "mcp-malicious.json").read_text(
            encoding="utf-8"
        ),
        encoding="utf-8",
    )
    runner = CliRunner()
    assert runner.invoke(app, ["allowlist", "init"]).exit_code == 0

    enforce_result = runner.invoke(app, ["allowlist", "enforce"])
    assert enforce_result.exit_code == 0
    assert "No violations." in enforce_result.stdout


def test_allowlist_enforce_flags_new_unlisted_server(tmp_path, monkeypatch):
    from mcphound.discovery import clients as discovery_clients

    fake_home = tmp_path / "home"
    fake_home.mkdir()
    monkeypatch.setattr(discovery_clients, "HOME", fake_home)
    monkeypatch.chdir(tmp_path)
    original = json.loads(
        (FIXTURES / "static" / "MCP-STATIC-001" / "mcp-malicious.json").read_text(
            encoding="utf-8"
        )
    )
    (tmp_path / ".mcp.json").write_text(json.dumps(original), encoding="utf-8")
    runner = CliRunner()
    assert runner.invoke(app, ["allowlist", "init"]).exit_code == 0

    original["mcpServers"]["new-tool"] = {"command": "npx", "args": ["-y", "@acme/new-tool@1.0.0"]}
    (tmp_path / ".mcp.json").write_text(json.dumps(original), encoding="utf-8")

    result = runner.invoke(app, ["allowlist", "enforce", "--json"])
    assert result.exit_code == 1
    violations = json.loads(result.stdout)
    kinds = {(v["kind"], v["server"]) for v in violations}
    assert ("unlisted_server", "@acme/new-tool") in kinds
    assert not any(v["kind"] == "finding" for v in violations)


def test_allowlist_enforce_json_and_markdown_together_errors(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "mcp-policy.yaml").write_text("mode: strict\n", encoding="utf-8")
    runner = CliRunner()
    result = runner.invoke(app, ["allowlist", "enforce", "--json", "--markdown"])
    assert result.exit_code == 2
    assert "--markdown" in result.output


def test_allowlist_enforce_markdown_output(tmp_path, monkeypatch):
    from mcphound.discovery import clients as discovery_clients

    fake_home = tmp_path / "home"
    fake_home.mkdir()
    monkeypatch.setattr(discovery_clients, "HOME", fake_home)
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".mcp.json").write_text(
        (FIXTURES / "static" / "MCP-STATIC-001" / "mcp-malicious.json").read_text(
            encoding="utf-8"
        ),
        encoding="utf-8",
    )
    runner = CliRunner()
    assert runner.invoke(app, ["allowlist", "init"]).exit_code == 0

    result = runner.invoke(app, ["allowlist", "enforce", "--markdown"])
    assert result.exit_code == 0
    assert "## mcphound allowlist check" in result.stdout
    assert "No violations." in result.stdout


def test_registry_export_defaults_out_dir_from_config(monkeypatch, tmp_path):
    from mcphound import cli as cli_module

    cfg_path = tmp_path / "registry.yaml"
    cfg_path.write_text(
        "registry:\n  base_url: https://registry.example\n  artifacts_dir: my-artifacts\n",
        encoding="utf-8",
    )
    fake_session = MagicMock()
    write_all_artifacts_mock = MagicMock(return_value=(0, 0))

    monkeypatch.setattr(cli_module, "get_session_factory", lambda: lambda: fake_session)
    monkeypatch.setattr(cli_module, "write_all_artifacts", write_all_artifacts_mock)

    runner = CliRunner()
    result = runner.invoke(app, ["registry-export", "--config", str(cfg_path)])

    assert result.exit_code == 0
    called_out_dir = write_all_artifacts_mock.call_args.args[1]
    assert str(called_out_dir) == "my-artifacts"

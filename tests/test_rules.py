from mcphound.discovery.clients import load_servers
from mcphound.output import to_sarif
from mcphound.rules.engine import evaluate
from mcphound.rules.loader import load_rules
from tests.conftest import fixture_path

RULES = load_rules()


def _finding_ids(fixture: str, rule_dir: str):
    servers = load_servers(fixture_path(rule_dir, fixture))
    return {f.rule_id for f in evaluate(servers[0], RULES)}


def test_secret_rule_fires_on_literal_token():
    assert "MCP-STATIC-001" in _finding_ids("mcp-malicious.json", "MCP-STATIC-001")


def test_secret_rule_allows_env_expansion():
    assert "MCP-STATIC-001" not in _finding_ids("mcp-benign.json", "MCP-STATIC-001")


def test_pipe_to_shell_fires():
    assert "MCP-STATIC-002" in _finding_ids("mcp-malicious.json", "MCP-STATIC-002")


def test_pinned_npx_is_clean():
    assert "MCP-STATIC-002" not in _finding_ids("mcp-benign.json", "MCP-STATIC-002")


def test_overbroad_permissions_rule_fires_on_privileged_docker():
    assert "MCP-STATIC-003" in _finding_ids("mcp-malicious.json", "MCP-STATIC-003")


def test_overbroad_permissions_rule_allows_scoped_mount():
    assert "MCP-STATIC-003" not in _finding_ids("mcp-benign.json", "MCP-STATIC-003")


def test_unpinned_version_rule_fires_on_latest_tag():
    assert "MCP-STATIC-004" in _finding_ids("mcp-malicious.json", "MCP-STATIC-004")


def test_unpinned_version_rule_allows_pinned_version():
    assert "MCP-STATIC-004" not in _finding_ids("mcp-benign.json", "MCP-STATIC-004")


def test_description_injection_rule_fires_on_hidden_comment_and_zero_width():
    assert "MCP-STATIC-005" in _finding_ids("mcp-malicious.json", "MCP-STATIC-005")


def test_description_injection_rule_allows_plain_description():
    assert "MCP-STATIC-005" not in _finding_ids("mcp-benign.json", "MCP-STATIC-005")


def test_typosquat_rule_fires_on_near_miss_name():
    assert "MCP-STATIC-006" in _finding_ids("mcp-malicious.json", "MCP-STATIC-006")


def test_typosquat_rule_allows_exact_known_name():
    assert "MCP-STATIC-006" not in _finding_ids("mcp-benign.json", "MCP-STATIC-006")


def test_npm_provenance_rule_fires_on_missing_repository(monkeypatch):
    from mcphound.rules import engine

    monkeypatch.setattr(
        engine,
        "_fetch_npm_metadata",
        lambda pkg: {"dist-tags": {"latest": "1.0.0"}, "versions": {"1.0.0": {}}},
    )
    assert "MCP-STATIC-007" in _finding_ids("mcp-malicious.json", "MCP-STATIC-007")


def test_npm_provenance_rule_allows_package_with_repository(monkeypatch):
    from mcphound.rules import engine

    monkeypatch.setattr(
        engine,
        "_fetch_npm_metadata",
        lambda pkg: {
            "dist-tags": {"latest": "1.0.0"},
            "versions": {
                "1.0.0": {"repository": {"type": "git", "url": "https://github.com/example/repo"}}
            },
        },
    )
    assert "MCP-STATIC-007" not in _finding_ids("mcp-benign.json", "MCP-STATIC-007")


def test_npm_provenance_rule_skips_silently_on_network_failure(monkeypatch):
    from mcphound.rules import engine

    monkeypatch.setattr(engine, "_fetch_npm_metadata", lambda pkg: None)
    assert "MCP-STATIC-007" not in _finding_ids("mcp-malicious.json", "MCP-STATIC-007")


def test_npm_provenance_rule_is_marked_network():
    rule = next(r for r in RULES if r["id"] == "MCP-STATIC-007")
    assert rule.get("network") is True


def test_every_finding_is_owasp_mapped():
    for rule in RULES:
        assert rule.get("owasp"), f"{rule['id']} is missing an OWASP mapping"


def test_sarif_serializes():
    servers = load_servers(fixture_path("MCP-STATIC-002", "mcp-malicious.json"))
    findings = evaluate(servers[0], RULES)
    from mcphound.models import ScanResult

    sarif = to_sarif(ScanResult(servers=servers, findings=findings))
    assert sarif["version"] == "2.1.0"
    assert sarif["runs"][0]["results"], "expected at least one SARIF result"

from mcpvet.discovery.clients import load_servers
from mcpvet.output import to_sarif
from mcpvet.rules.engine import evaluate
from mcpvet.rules.loader import load_rules
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


def test_every_finding_is_owasp_mapped():
    for rule in RULES:
        assert rule.get("owasp"), f"{rule['id']} is missing an OWASP mapping"


def test_sarif_serializes():
    servers = load_servers(fixture_path("MCP-STATIC-002", "mcp-malicious.json"))
    findings = evaluate(servers[0], RULES)
    from mcpvet.models import ScanResult

    sarif = to_sarif(ScanResult(servers=servers, findings=findings))
    assert sarif["version"] == "2.1.0"
    assert sarif["runs"][0]["results"], "expected at least one SARIF result"

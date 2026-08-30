from __future__ import annotations

from mcphound import __version__
from mcphound.registry.artifacts import escape_name_component
from mcphound.registry.scanner import run_scan, run_scoring
from mcphound.rules.loader import load_rules

RULES = load_rules()


def test_read_server_returns_score_and_findings(client, db_session_fixture, seed_version):
    server, _ = seed_version(
        server_name="io.github.acme/tool",
        environment_variables=[{"name": "API_KEY", "value": "sk-abcdefghijklmnop"}],
    )
    run_scan(db_session_fixture, RULES, __version__)
    run_scoring(db_session_fixture, __version__)
    slug = escape_name_component(server.name)

    response = client.get(f"/v1/servers/{slug}")

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "io.github.acme/tool"
    assert body["score"] == 65
    assert body["finding_count"] == 1
    assert body["findings"][0]["rule_id"] == "MCP-STATIC-001"


def test_read_server_404s_for_unknown_slug(client):
    response = client.get("/v1/servers/does-not-exist")

    assert response.status_code == 404
    assert response.json() == {"detail": "server not scored"}

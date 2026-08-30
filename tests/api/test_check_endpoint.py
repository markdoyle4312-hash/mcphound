from __future__ import annotations

from mcphound import __version__
from mcphound.registry.artifacts import escape_name_component
from mcphound.registry.scanner import run_scan, run_scoring
from mcphound.rules.loader import load_rules

RULES = load_rules()


def test_check_finds_a_scored_server(client, db_session_fixture, seed_version):
    server, _ = seed_version(server_name="io.github.acme/tool")
    run_scan(db_session_fixture, RULES, __version__)
    run_scoring(db_session_fixture, __version__)

    response = client.get("/v1/check", params={"name": "io.github.acme/tool"})

    assert response.status_code == 200
    body = response.json()
    assert body["found"] is True
    assert body["score"] == 100
    assert body["slug"] == escape_name_component(server.name)
    assert body["report_url"].endswith(f"/servers/{body['slug']}")


def test_check_returns_found_false_for_unknown_name(client):
    response = client.get("/v1/check", params={"name": "io.github.nope/nothing"})

    assert response.status_code == 200
    assert response.json() == {
        "found": False,
        "name": "io.github.nope/nothing",
        "slug": None,
        "score": None,
        "finding_count": None,
        "report_url": None,
    }

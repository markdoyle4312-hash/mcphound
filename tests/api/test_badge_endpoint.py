from __future__ import annotations

from mcphound import __version__
from mcphound.registry.artifacts import escape_name_component
from mcphound.registry.scanner import run_scan, run_scoring
from mcphound.rules.loader import load_rules

RULES = load_rules()


def test_badge_route_returns_svg_for_a_scored_server(client, db_session_fixture, seed_version):
    server, _ = seed_version(server_name="io.github.acme/tool")
    run_scan(db_session_fixture, RULES, __version__)
    run_scoring(db_session_fixture, __version__)
    slug = escape_name_component(server.name)

    response = client.get(f"/v1/badge/{slug}.svg")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("image/svg+xml")
    assert response.headers["cache-control"] == "public, max-age=3600"
    assert b"<svg" in response.content


def test_badge_route_404s_for_unknown_slug(client):
    response = client.get("/v1/badge/does-not-exist.svg")

    assert response.status_code == 404

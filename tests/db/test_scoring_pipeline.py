from __future__ import annotations

from mcphound import __version__
from mcphound.db.models import ServerScore
from mcphound.registry.scanner import run_scan, run_scoring
from mcphound.rules.loader import load_rules

RULES = load_rules()


def test_run_scoring_gives_a_clean_server_a_perfect_score(db_session_fixture, seed_version):
    server, _ = seed_version()
    run_scan(db_session_fixture, RULES, __version__)

    summary = run_scoring(db_session_fixture, __version__)

    assert summary.servers_scored == 1
    row = db_session_fixture.query(ServerScore).filter_by(server_id=server.id).one()
    assert row.score == 100
    assert row.finding_count == 0


def test_run_scoring_penalizes_a_flagged_server(db_session_fixture, seed_version):
    server, _ = seed_version(
        environment_variables=[{"name": "API_KEY", "value": "sk-abcdefghijklmnop"}]
    )
    run_scan(db_session_fixture, RULES, __version__)

    run_scoring(db_session_fixture, __version__)

    row = db_session_fixture.query(ServerScore).filter_by(server_id=server.id).one()
    # MCP-STATIC-001 is severity=high confidence=high: 100 * (1 - 0.35) = 65
    assert row.score == 65
    assert row.finding_count == 1


def test_run_scoring_unions_findings_across_a_servers_multiple_latest_versions(
    db_session_fixture, seed_version
):
    server_name = "io.github.acme/multi"
    server, _ = seed_version(server_name=server_name, registry_type="npm", identifier="@acme/multi")
    seed_version(
        server_name=server_name,
        registry_type="remote",
        identifier="https://acme.example/mcp",
        environment_variables=[{"name": "API_KEY", "value": "sk-abcdefghijklmnop"}],
    )
    run_scan(db_session_fixture, RULES, __version__)

    run_scoring(db_session_fixture, __version__)

    row = db_session_fixture.query(ServerScore).filter_by(server_id=server.id).one()
    assert row.finding_count == 1
    assert row.score == 65

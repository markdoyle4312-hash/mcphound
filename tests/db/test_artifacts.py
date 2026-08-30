from __future__ import annotations

import json

from mcphound import __version__
from mcphound.registry.artifacts import write_artifacts
from mcphound.registry.scanner import run_scan, run_scoring
from mcphound.rules.loader import load_rules

RULES = load_rules()


def test_write_artifacts_writes_a_per_server_file_and_an_index(
    db_session_fixture, seed_version, tmp_path
):
    server, _ = seed_version(
        environment_variables=[{"name": "API_KEY", "value": "sk-abcdefghijklmnop"}]
    )
    run_scan(db_session_fixture, RULES, __version__)
    run_scoring(db_session_fixture, __version__)

    written = write_artifacts(db_session_fixture, tmp_path)

    assert written == 1
    server_file = tmp_path / "servers" / "io.github.acme__tool.json"
    assert server_file.exists()
    payload = json.loads(server_file.read_text(encoding="utf-8"))
    assert payload["name"] == server.name
    assert payload["score"] == 65
    assert payload["finding_count"] == 1
    assert payload["findings"][0]["rule_id"] == "MCP-STATIC-001"

    index = json.loads((tmp_path / "index.json").read_text(encoding="utf-8"))
    assert index == [
        {
            "name": server.name,
            "score": 65,
            "finding_count": 1,
            "last_scanned_at": payload["computed_at"],
        }
    ]


def test_write_artifacts_disambiguates_case_colliding_names(
    db_session_fixture, seed_version, tmp_path
):
    """Two registry names differing only by case escape to the same filename
    on a case-insensitive filesystem (NTFS) — the second must not silently
    clobber the first."""
    seed_version(server_name="io.github.Foo/bar")
    seed_version(server_name="io.github.foo/bar")
    run_scan(db_session_fixture, RULES, __version__)
    run_scoring(db_session_fixture, __version__)

    written = write_artifacts(db_session_fixture, tmp_path)

    assert written == 2
    files = sorted(p.name for p in (tmp_path / "servers").glob("*.json"))
    assert len(files) == 2
    assert files[0].lower() != files[1].lower()
    index = json.loads((tmp_path / "index.json").read_text(encoding="utf-8"))
    assert {row["name"] for row in index} == {"io.github.Foo/bar", "io.github.foo/bar"}


def test_write_artifacts_skips_servers_with_no_score_yet(
    db_session_fixture, seed_version, tmp_path
):
    seed_version()  # never scanned or scored

    written = write_artifacts(db_session_fixture, tmp_path)

    assert written == 0
    assert json.loads((tmp_path / "index.json").read_text(encoding="utf-8")) == []


def test_write_artifacts_escapes_slashes_in_server_names(
    db_session_fixture, seed_version, tmp_path
):
    seed_version(server_name="io.github.acme/weird name!")
    run_scan(db_session_fixture, RULES, __version__)
    run_scoring(db_session_fixture, __version__)

    write_artifacts(db_session_fixture, tmp_path)

    assert (tmp_path / "servers" / "io.github.acme__weird_name_.json").exists()

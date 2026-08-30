from __future__ import annotations

import json

from mcphound import __version__
from mcphound.registry.artifacts import (
    write_all_artifacts,
    write_artifacts,
    write_typosquat_clusters,
)
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
            "slug": "io.github.acme__tool",
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
    slugs = {row["slug"] for row in index}
    assert slugs == {f.removesuffix(".json") for f in files}


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
    index = json.loads((tmp_path / "index.json").read_text(encoding="utf-8"))
    assert index[0]["slug"] == "io.github.acme__weird_name_"


def test_write_typosquat_clusters_finds_near_miss_packages(
    db_session_fixture, seed_version, tmp_path
):
    seed_version(
        server_name="io.github.acme/lookalike",
        registry_type="npm",
        identifier="@modelcontextprotocol/server-filesystemx",
    )
    run_scan(db_session_fixture, RULES, __version__)
    run_scoring(db_session_fixture, __version__)
    write_artifacts(db_session_fixture, tmp_path)

    write_typosquat_clusters(db_session_fixture, tmp_path, RULES)

    clusters = json.loads((tmp_path / "typosquat-clusters.json").read_text(encoding="utf-8"))
    entry = next(
        c for c in clusters if c["known_name"] == "@modelcontextprotocol/server-filesystem"
    )
    assert entry["known_slug"] == "@modelcontextprotocol__server-filesystem"
    assert entry["neighbors"] == [
        {
            "identifier": "@modelcontextprotocol/server-filesystemx",
            "distance": 1,
            "server_name": "io.github.acme/lookalike",
            "server_slug": "io.github.acme__lookalike",
        }
    ]


def test_write_typosquat_clusters_excludes_exact_matches(
    db_session_fixture, seed_version, tmp_path
):
    seed_version(
        server_name="io.github.acme/exact",
        registry_type="npm",
        identifier="@modelcontextprotocol/server-filesystem",
    )

    write_typosquat_clusters(db_session_fixture, tmp_path, RULES)

    clusters = json.loads((tmp_path / "typosquat-clusters.json").read_text(encoding="utf-8"))
    entry = next(
        c for c in clusters if c["known_name"] == "@modelcontextprotocol/server-filesystem"
    )
    assert entry["neighbors"] == []


def test_write_typosquat_clusters_covers_every_known_name(db_session_fixture, tmp_path):
    write_typosquat_clusters(db_session_fixture, tmp_path, RULES)

    clusters = json.loads((tmp_path / "typosquat-clusters.json").read_text(encoding="utf-8"))
    known_names = {c["known_name"] for c in clusters}
    assert "@modelcontextprotocol/server-filesystem" in known_names
    assert all(c["neighbors"] == [] for c in clusters)


def test_write_all_artifacts_writes_both_files(db_session_fixture, seed_version, tmp_path):
    seed_version()
    run_scan(db_session_fixture, RULES, __version__)
    run_scoring(db_session_fixture, __version__)

    written, clustered = write_all_artifacts(db_session_fixture, tmp_path, RULES)

    assert written == 1
    assert clustered == 0
    assert (tmp_path / "index.json").exists()
    assert (tmp_path / "typosquat-clusters.json").exists()

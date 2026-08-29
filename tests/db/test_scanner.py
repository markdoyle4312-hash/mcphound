from __future__ import annotations

import datetime as dt

from mcphound import __version__
from mcphound.db.models import Finding as FindingRow
from mcphound.db.models import Hash, Scan
from mcphound.registry.scanner import run_scan
from mcphound.rules.loader import load_rules

RULES = load_rules()


def test_run_scan_flags_a_hardcoded_secret_in_env(db_session_fixture, seed_version):
    _, version = seed_version(
        environment_variables=[{"name": "API_KEY", "value": "sk-abcdefghijklmnop"}]
    )

    summary = run_scan(db_session_fixture, RULES, __version__)

    assert summary.versions_seen == 1
    assert summary.versions_scanned == 1
    scan = db_session_fixture.query(Scan).filter_by(version_id=version.id).one()
    assert scan.status == "ok"
    findings = db_session_fixture.query(FindingRow).filter_by(scan_id=scan.id).all()
    assert any(f.rule_id == "MCP-STATIC-001" for f in findings)


def test_run_scan_produces_no_findings_for_a_clean_version(db_session_fixture, seed_version):
    seed_version()

    summary = run_scan(db_session_fixture, RULES, __version__)

    assert summary.versions_scanned == 1
    assert summary.findings_written == 0


def test_run_scan_ignores_versions_that_are_not_latest(db_session_fixture, seed_version):
    seed_version(is_latest=False)

    summary = run_scan(db_session_fixture, RULES, __version__)

    assert summary.versions_seen == 0


def test_run_scan_ignores_delisted_versions(db_session_fixture, seed_version):
    seed_version(delisted_at=dt.datetime.now(dt.UTC))

    summary = run_scan(db_session_fixture, RULES, __version__)

    assert summary.versions_seen == 0


def test_run_scan_skips_a_version_already_scanned_with_no_new_hash(
    db_session_fixture, seed_version
):
    _, version = seed_version()
    db_session_fixture.add(Hash(version_id=version.id, sha256="hash-v1"))
    db_session_fixture.flush()

    run_scan(db_session_fixture, RULES, __version__)
    second = run_scan(db_session_fixture, RULES, __version__)

    assert second.versions_scanned == 0
    assert second.versions_skipped == 1


def test_run_scan_rescans_when_a_new_hash_is_observed(db_session_fixture, seed_version):
    _, version = seed_version()
    db_session_fixture.add(Hash(version_id=version.id, sha256="hash-v1"))
    db_session_fixture.flush()
    run_scan(db_session_fixture, RULES, __version__)

    db_session_fixture.add(Hash(version_id=version.id, sha256="hash-v2"))
    db_session_fixture.flush()
    second = run_scan(db_session_fixture, RULES, __version__)

    assert second.versions_scanned == 1
    assert second.versions_skipped == 0


def test_run_scan_isolates_a_failing_version_and_marks_it_errored(
    db_session_fixture, seed_version, monkeypatch
):
    from mcphound.registry import scanner as scanner_module

    seed_version()

    def _boom(version):
        raise ValueError("synthetic adapter failure")

    monkeypatch.setattr(scanner_module, "version_to_server_config", _boom)

    summary = run_scan(db_session_fixture, RULES, __version__)

    assert summary.versions_errored == 1
    assert summary.versions_scanned == 0
    scan = db_session_fixture.query(Scan).one()
    assert scan.status == "error"

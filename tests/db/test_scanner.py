from __future__ import annotations

import datetime as dt
import threading

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


def test_run_scan_isolates_a_version_whose_evaluate_call_raises(
    db_session_fixture, seed_version, monkeypatch
):
    """evaluate() itself (not just version_to_server_config) runs on the
    thread pool — its failures surface via future.result() in a separate
    except block, so this needs its own coverage rather than assuming the
    version_to_server_config isolation test above covers both paths."""
    from mcphound.registry import scanner as scanner_module

    seed_version()

    def _boom(server_config, rules):
        raise ValueError("synthetic evaluate failure")

    monkeypatch.setattr(scanner_module, "evaluate", _boom)

    summary = run_scan(db_session_fixture, RULES, __version__)

    assert summary.versions_errored == 1
    assert summary.versions_scanned == 0
    scan = db_session_fixture.query(Scan).one()
    assert scan.status == "error"


def test_run_scan_evaluates_versions_concurrently(db_session_fixture, seed_version, monkeypatch):
    """Proves real parallelism (not just an API surface change): n versions'
    evaluate() calls must all be in flight at once to clear the barrier. On
    the old sequential loop this times out and every version gets marked
    errored, so versions_scanned stays 0 and the assertion below fails."""
    from mcphound.registry import scanner as scanner_module

    n = 4
    for i in range(n):
        seed_version(server_name=f"io.github.acme/tool-{i}")

    barrier = threading.Barrier(n, timeout=2)

    def fake_evaluate(server_config, rules):
        barrier.wait()
        return []

    monkeypatch.setattr(scanner_module, "evaluate", fake_evaluate)

    summary = run_scan(db_session_fixture, RULES, __version__, max_workers=n)

    assert summary.versions_scanned == n
    assert summary.versions_errored == 0

from __future__ import annotations

from mcphound.models import Finding
from mcphound.policy import Policy, check_findings, fingerprint, load_baseline, write_baseline


def _finding(rule_id="MCP-STATIC-004", server="acme", severity="high", location="cfg :: acme"):
    return Finding(rule_id=rule_id, title="t", severity=severity, server=server, location=location)


def test_fingerprint_is_stable_for_an_equivalent_finding():
    assert fingerprint(_finding()) == fingerprint(_finding())


def test_fingerprint_differs_by_rule_id():
    a = fingerprint(_finding(rule_id="MCP-STATIC-004"))
    b = fingerprint(_finding(rule_id="MCP-STATIC-005"))
    assert a != b


def test_load_baseline_missing_file_returns_empty_set(tmp_path):
    assert load_baseline(tmp_path / "missing.json") == set()


def test_write_and_load_baseline_round_trip(tmp_path):
    path = tmp_path / "baseline.json"
    findings = [_finding()]
    write_baseline(path, findings)
    assert load_baseline(path) == {fingerprint(findings[0])}


def test_check_findings_strict_mode_flags_everything_above_fail_on():
    policy = Policy(mode="strict", fail_on="medium")
    findings = [_finding(severity="high"), _finding(rule_id="MCP-STATIC-001", severity="low")]
    violations = check_findings(findings, policy, baseline=set())
    assert len(violations) == 1
    assert violations[0].rule_id == "MCP-STATIC-004"


def test_check_findings_baseline_mode_suppresses_known_findings():
    known = _finding(severity="high")
    new = _finding(rule_id="MCP-STATIC-099", severity="high")
    policy = Policy(mode="baseline", fail_on="medium")
    baseline = {fingerprint(known)}
    violations = check_findings([known, new], policy, baseline)
    assert len(violations) == 1
    assert violations[0].rule_id == "MCP-STATIC-099"

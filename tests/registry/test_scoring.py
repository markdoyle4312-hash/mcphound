from mcphound.registry.scoring import dedupe_by_rule_id, score_server


class _F:
    def __init__(self, rule_id, severity, confidence):
        self.rule_id = rule_id
        self.severity = severity
        self.confidence = confidence


def test_score_server_with_no_findings_is_100():
    assert score_server([]) == 100


def test_score_server_single_critical_high_confidence_finding():
    # 100 * (1 - 0.55 * 1.0) = 45
    assert score_server([_F("R1", "critical", "high")]) == 45


def test_score_server_single_high_high_confidence_finding():
    # 100 * (1 - 0.35 * 1.0) = 65
    assert score_server([_F("R1", "high", "high")]) == 65


def test_score_server_low_confidence_dampens_the_hit():
    # 100 * (1 - 0.55 * 0.4) = 78
    assert score_server([_F("R1", "critical", "low")]) == 78


def test_score_server_is_monotonically_non_increasing_with_more_findings():
    one_finding = score_server([_F("R1", "medium", "medium")])
    two_findings = score_server([_F("R1", "medium", "medium"), _F("R2", "low", "low")])
    assert two_findings <= one_finding


def test_score_server_never_goes_below_zero():
    many_criticals = [_F(f"R{i}", "critical", "high") for i in range(50)]
    assert score_server(many_criticals) == 0


def test_dedupe_by_rule_id_keeps_the_max_severity_confidence_pair():
    findings = [_F("R1", "low", "low"), _F("R1", "critical", "high")]
    result = dedupe_by_rule_id(findings)
    assert len(result) == 1
    assert result[0].severity == "critical"
    assert result[0].confidence == "high"


def test_dedupe_by_rule_id_preserves_distinct_rule_ids():
    findings = [_F("R1", "low", "low"), _F("R2", "high", "high")]
    assert {f.rule_id for f in dedupe_by_rule_id(findings)} == {"R1", "R2"}


def test_dedupe_by_rule_id_on_empty_list():
    assert dedupe_by_rule_id([]) == []

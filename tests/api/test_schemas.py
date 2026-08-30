from __future__ import annotations

import datetime as dt

from mcphound.api.schemas import CheckResult, Finding, ServerDetail


def test_server_detail_parses_a_plain_dict():
    detail = ServerDetail(
        name="io.github.acme/tool",
        slug="io.github.acme__tool",
        score=87,
        finding_count=1,
        last_scanned_at=dt.datetime(2026, 8, 30, tzinfo=dt.UTC),
        findings=[
            {
                "rule_id": "MCP-STATIC-001",
                "title": "Hardcoded secret",
                "severity": "high",
                "confidence": "high",
                "owasp": "LLM07",
                "detail": "found a key",
                "recommendation": "use env vars",
            }
        ],
    )

    assert detail.score == 87
    assert isinstance(detail.findings[0], Finding)
    assert detail.findings[0].rule_id == "MCP-STATIC-001"


def test_check_result_defaults_optional_fields_to_none():
    result = CheckResult(found=False, name="io.github.nope/nothing")

    assert result.slug is None
    assert result.score is None
    assert result.finding_count is None
    assert result.report_url is None

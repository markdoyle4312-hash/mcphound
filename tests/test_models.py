from __future__ import annotations

from mcphound.models import PolicyViolation


def test_policy_violation_defaults():
    v = PolicyViolation(kind="unlisted_server", severity="high", detail="not allowed")
    assert v.server is None
    assert v.rule_id is None


def test_policy_violation_round_trips_through_json():
    v = PolicyViolation(
        kind="finding", server="acme-tool", rule_id="MCP-STATIC-004", severity="medium",
        detail="unpinned version",
    )
    data = v.model_dump()
    assert data == {
        "kind": "finding",
        "server": "acme-tool",
        "rule_id": "MCP-STATIC-004",
        "severity": "medium",
        "detail": "unpinned version",
    }

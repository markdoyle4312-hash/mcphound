from __future__ import annotations

from pathlib import Path

from mcphound.models import PolicyViolation
from mcphound.policy import render_markdown


def test_render_markdown_no_violations():
    text = render_markdown([], server_count=2, policy_path=Path("mcp-policy.yaml"))
    assert "Checked 2 server(s) against `mcp-policy.yaml`." in text
    assert "No violations." in text


def test_render_markdown_lists_violations_in_a_table():
    violations = [
        PolicyViolation(
            kind="unlisted_server",
            server="@acme/new-tool",
            severity="high",
            detail='"@acme/new-tool" is not in the mcp-policy.yaml allowlist',
        ),
        PolicyViolation(
            kind="finding",
            server="evil",
            rule_id="MCP-STATIC-001",
            severity="high",
            detail="Hardcoded secret in MCP server environment",
        ),
    ]
    text = render_markdown(violations, server_count=3, policy_path=Path("mcp-policy.yaml"))
    assert "**2 violation(s):**" in text
    assert "| unlisted_server | `@acme/new-tool` |" in text
    assert "| finding | `evil` |" in text


def test_render_markdown_uses_dash_for_missing_server():
    violations = [PolicyViolation(kind="finding", server=None, severity="low", detail="x")]
    text = render_markdown(violations, server_count=1, policy_path=Path("mcp-policy.yaml"))
    assert "| finding | - | x |" in text

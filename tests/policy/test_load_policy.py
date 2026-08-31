from __future__ import annotations

import pytest

from mcphound.policy import PolicyError, load_policy


def _write(tmp_path, text):
    p = tmp_path / "mcp-policy.yaml"
    p.write_text(text, encoding="utf-8")
    return p


def test_load_policy_valid_round_trip(tmp_path):
    p = _write(
        tmp_path,
        """
mode: baseline
fail_on: high
blocked_registries:
  - shady.example.com
servers:
  - name: "@acme/tool"
    version: "1.0.0"
""",
    )
    policy = load_policy(p)
    assert policy.mode == "baseline"
    assert policy.fail_on == "high"
    assert policy.blocked_registries == ["shady.example.com"]
    assert policy.servers[0].name == "@acme/tool"
    assert policy.servers[0].version == "1.0.0"


def test_load_policy_defaults_for_minimal_file(tmp_path):
    p = _write(tmp_path, "servers: []\n")
    policy = load_policy(p)
    assert policy.mode == "strict"
    assert policy.fail_on == "medium"
    assert policy.blocked_registries == []


def test_load_policy_rejects_malformed_yaml(tmp_path):
    p = _write(tmp_path, "mode: [unclosed")
    with pytest.raises(PolicyError):
        load_policy(p)


def test_load_policy_rejects_unknown_mode(tmp_path):
    p = _write(tmp_path, "mode: yolo\n")
    with pytest.raises(PolicyError):
        load_policy(p)


def test_load_policy_rejects_unknown_fail_on(tmp_path):
    p = _write(tmp_path, "fail_on: extreme\n")
    with pytest.raises(PolicyError):
        load_policy(p)


def test_load_policy_rejects_both_version_and_digest(tmp_path):
    p = _write(
        tmp_path,
        """
servers:
  - name: "@acme/tool"
    version: "1.0.0"
    digest: "sha256:abc"
""",
    )
    with pytest.raises(PolicyError):
        load_policy(p)

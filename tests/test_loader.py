from mcphound.rules.loader import load_rules, rules_fingerprint


def test_fingerprint_is_stable_for_same_rules():
    rules = load_rules()
    assert rules_fingerprint(rules) == rules_fingerprint(rules)


def test_fingerprint_has_rules_prefix():
    assert rules_fingerprint(load_rules()).startswith("rules-")


def test_fingerprint_changes_when_rule_content_changes():
    base = [{"id": "MCP-STATIC-999", "title": "x"}]
    changed = [{"id": "MCP-STATIC-999", "title": "y"}]
    assert rules_fingerprint(base) != rules_fingerprint(changed)


def test_fingerprint_is_order_independent():
    a = [{"id": "MCP-STATIC-001"}, {"id": "MCP-STATIC-002"}]
    b = [{"id": "MCP-STATIC-002"}, {"id": "MCP-STATIC-001"}]
    assert rules_fingerprint(a) == rules_fingerprint(b)

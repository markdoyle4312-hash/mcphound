"""W7 false-positive-sweep regression guard.

registry_top50.json holds real, source-verified MCP server configs (see SOURCES.md).
The sweep (documented in CHANGELOG.md) found MCP-STATIC-004 and MCP-STATIC-007 are the
only rules that legitimately fire on this corpus, and those firings are expected true
positives (unpinned/@latest installs, and archived reference servers missing npm
`repository` metadata) — not something a scan of this corpus should ever be silent on.

This test locks that in: any OTHER rule firing here is a new false positive that needs
the same tune-and-document treatment as the original sweep, and a change that makes 004
or 007 stop firing on their known-true-positive servers is a detection regression.
"""

from __future__ import annotations

from pathlib import Path

from mcphound.discovery.clients import load_servers
from mcphound.rules import engine
from mcphound.rules.engine import evaluate
from mcphound.rules.loader import load_rules

CORPUS = Path(__file__).parent / "registry_top50.json"
RULES = load_rules()

# Every npx-launched package in the corpus is treated as an actively maintained registry
# entry by default — provenance is exercised deterministically here (no live network call
# in the test suite), same pattern as test_rules.py.
_FAKE_NPM_METADATA_WITH_REPO = {
    "dist-tags": {"latest": "1.0.0"},
    "versions": {"1.0.0": {"repository": {"type": "git", "url": "https://example.com/repo"}}},
}

# A successful registry response with no `repository` field — distinct from a fetch
# failure (None), which _evaluate_npm_provenance deliberately fails open on.
_FAKE_NPM_METADATA_NO_REPO = {"dist-tags": {"latest": "1.0.0"}, "versions": {"1.0.0": {}}}

# npm package-name substrings for the three archived/deprecated official reference servers
# confirmed (against the live registry, during the W7 sweep) to have no `repository` field.
_PACKAGES_MISSING_REPO = ("server-brave-search", "server-puppeteer", "server-google-maps")

# The server (config key) names those three packages correspond to in registry_top50.json.
_EXPECTED_007_HITS = {"brave-search", "puppeteer", "google-maps"}

_EXPECTED_RULES = {"MCP-STATIC-004", "MCP-STATIC-007"}


def test_corpus_only_fires_known_rules(monkeypatch):
    def fake_fetch(pkg: str) -> dict | None:
        if any(missing in pkg for missing in _PACKAGES_MISSING_REPO):
            return _FAKE_NPM_METADATA_NO_REPO
        return _FAKE_NPM_METADATA_WITH_REPO

    monkeypatch.setattr(engine, "_fetch_npm_metadata", fake_fetch)

    servers = load_servers(CORPUS)
    assert len(servers) >= 30, "corpus shrank unexpectedly — check registry_top50.json"

    unexpected: list[str] = []
    hit_007: set[str] = set()
    for server in servers:
        for finding in evaluate(server, RULES):
            if finding.rule_id not in _EXPECTED_RULES:
                unexpected.append(f"{finding.rule_id} on {server.name}: {finding.detail}")
            if finding.rule_id == "MCP-STATIC-007":
                hit_007.add(server.name)

    assert not unexpected, f"new false positive(s) on real-world corpus: {unexpected}"
    assert hit_007 == _EXPECTED_007_HITS, (
        f"MCP-STATIC-007 hit set changed: expected {_EXPECTED_007_HITS}, got {hit_007} "
        "— either a detection regression or a genuine npm metadata change worth re-verifying"
    )

from __future__ import annotations

from mcphound import __version__
from mcphound.api.queries import get_server_by_name, get_server_by_slug
from mcphound.registry.artifacts import _safe_filename, escape_name_component
from mcphound.registry.scanner import run_scan, run_scoring
from mcphound.rules.loader import load_rules

RULES = load_rules()


def test_get_server_by_name_returns_none_when_unscored(db_session_fixture, seed_version):
    seed_version(server_name="io.github.acme/unscored")

    result = get_server_by_name(db_session_fixture, "io.github.acme/unscored")

    assert result is None


def test_get_server_by_name_returns_score_and_findings(db_session_fixture, seed_version):
    seed_version(
        server_name="io.github.acme/tool",
        environment_variables=[{"name": "API_KEY", "value": "sk-abcdefghijklmnop"}],
    )
    run_scan(db_session_fixture, RULES, __version__)
    run_scoring(db_session_fixture, __version__)

    result = get_server_by_name(db_session_fixture, "io.github.acme/tool")

    assert result is not None
    assert result.name == "io.github.acme/tool"
    assert result.slug == escape_name_component("io.github.acme/tool")
    assert result.score == 65
    assert result.finding_count == 1
    assert result.findings[0]["rule_id"] == "MCP-STATIC-001"


def test_get_server_by_slug_finds_a_non_colliding_server(db_session_fixture, seed_version):
    seed_version(server_name="io.github.acme/tool")
    run_scan(db_session_fixture, RULES, __version__)
    run_scoring(db_session_fixture, __version__)
    slug = escape_name_component("io.github.acme/tool")

    result = get_server_by_slug(db_session_fixture, slug)

    assert result is not None
    assert result.name == "io.github.acme/tool"
    assert result.score == 100


def test_get_server_by_slug_returns_none_for_unknown_slug(db_session_fixture):
    result = get_server_by_slug(db_session_fixture, "does-not-exist")

    assert result is None


def test_get_server_by_slug_resolves_a_case_collision_suffix(db_session_fixture, seed_version):
    seed_version(server_name="io.github.Foo/bar")
    seed_version(server_name="io.github.foo/bar")
    run_scan(db_session_fixture, RULES, __version__)
    run_scoring(db_session_fixture, __version__)

    seen: set[str] = set()
    first_slug = _safe_filename("io.github.Foo/bar", seen).removesuffix(".json")
    second_slug = _safe_filename("io.github.foo/bar", seen).removesuffix(".json")
    assert first_slug != second_slug  # sanity: the fixture data actually collides

    first = get_server_by_slug(db_session_fixture, first_slug)
    second = get_server_by_slug(db_session_fixture, second_slug)

    assert first is not None and first.name == "io.github.Foo/bar"
    assert second is not None and second.name == "io.github.foo/bar"

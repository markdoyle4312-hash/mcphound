from __future__ import annotations

from mcphound.registry.artifacts import _safe_filename


def test_safe_filename_escapes_slash_and_unsafe_chars():
    seen: set[str] = set()
    assert _safe_filename("io.github.acme/weird name!", seen) == "io.github.acme__weird_name_.json"


def test_safe_filename_disambiguates_case_insensitive_collision():
    seen: set[str] = set()
    first = _safe_filename("io.github.Foo/bar", seen)
    second = _safe_filename("io.github.foo/bar", seen)

    assert first == "io.github.Foo__bar.json"
    assert first.lower() != second.lower()
    assert second.startswith("io.github.foo__bar-")


def test_safe_filename_is_deterministic_for_the_same_collision():
    seen_a: set[str] = set()
    seen_b: set[str] = set()
    _safe_filename("io.github.Foo/bar", seen_a)
    _safe_filename("io.github.Foo/bar", seen_b)

    resolved_a = _safe_filename("io.github.foo/bar", seen_a)
    resolved_b = _safe_filename("io.github.foo/bar", seen_b)

    assert resolved_a == resolved_b

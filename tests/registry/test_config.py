from __future__ import annotations

from mcphound.registry.config import (
    DEFAULT_ARTIFACTS_DIR,
    DEFAULT_BASE_URL,
    DEFAULT_PAGE_LIMIT,
    load_config,
)


def test_load_config_applies_defaults_when_file_is_empty(tmp_path):
    path = tmp_path / "registry.yaml"
    path.write_text("", encoding="utf-8")

    cfg = load_config(path)

    assert cfg.base_url == DEFAULT_BASE_URL
    assert cfg.page_limit == DEFAULT_PAGE_LIMIT
    assert cfg.artifacts_dir == DEFAULT_ARTIFACTS_DIR


def test_load_config_applies_defaults_when_registry_key_is_missing(tmp_path):
    path = tmp_path / "registry.yaml"
    path.write_text("unrelated: true\n", encoding="utf-8")

    cfg = load_config(path)

    assert cfg.base_url == DEFAULT_BASE_URL
    assert cfg.page_limit == DEFAULT_PAGE_LIMIT
    assert cfg.artifacts_dir == DEFAULT_ARTIFACTS_DIR


def test_load_config_applies_defaults_per_field_when_partially_set(tmp_path):
    path = tmp_path / "registry.yaml"
    path.write_text("registry:\n  base_url: https://example.test\n", encoding="utf-8")

    cfg = load_config(path)

    assert cfg.base_url == "https://example.test"
    assert cfg.page_limit == DEFAULT_PAGE_LIMIT
    assert cfg.artifacts_dir == DEFAULT_ARTIFACTS_DIR


def test_load_config_honors_every_explicit_value(tmp_path):
    path = tmp_path / "registry.yaml"
    path.write_text(
        "registry:\n  base_url: https://example.test\n  page_limit: 25\n  artifacts_dir: out\n",
        encoding="utf-8",
    )

    cfg = load_config(path)

    assert cfg.base_url == "https://example.test"
    assert cfg.page_limit == 25
    assert cfg.artifacts_dir == "out"


def test_load_config_coerces_page_limit_to_int(tmp_path):
    """YAML can parse an unquoted page_limit as a string in edge cases
    (e.g. inside an env-substituted template) — load_config must not hand
    a str down to code that expects int."""
    path = tmp_path / "registry.yaml"
    path.write_text('registry:\n  page_limit: "50"\n', encoding="utf-8")

    cfg = load_config(path)

    assert cfg.page_limit == 50
    assert isinstance(cfg.page_limit, int)

from __future__ import annotations

from mcphound.models import ServerConfig
from mcphound.rules.typosquat import (
    extract_command_package,
    extract_command_version,
    load_reference_list,
    nearest_match,
    neighbors_of,
    typosquat_rule_config,
)


def _server(command: list[str]) -> ServerConfig:
    return ServerConfig(name="test", command=command)


def test_extract_command_package_from_npx():
    assert extract_command_package(_server(["npx", "-y", "@acme/tool@1.0.0"])) == "@acme/tool"


def test_extract_command_package_from_uvx():
    assert extract_command_package(_server(["uvx", "acme-tool@2.3.1"])) == "acme-tool"


def test_extract_command_package_returns_none_for_non_npx_uvx_launchers():
    assert extract_command_package(_server(["docker", "run", "ghcr.io/acme/tool"])) is None


def test_extract_command_package_returns_none_with_no_command():
    assert extract_command_package(_server([])) is None


def test_extract_command_version_from_npx_scoped_package():
    assert extract_command_version(_server(["npx", "-y", "@acme/tool@1.0.0"])) == "1.0.0"


def test_extract_command_version_from_uvx_unscoped_package():
    assert extract_command_version(_server(["uvx", "acme-tool@2.3.1"])) == "2.3.1"


def test_extract_command_version_returns_none_when_unpinned():
    assert extract_command_version(_server(["npx", "-y", "@acme/tool"])) is None


def test_extract_command_version_returns_none_for_non_npx_uvx_launchers():
    assert extract_command_version(_server(["docker", "run", "ghcr.io/acme/tool:1.0.0"])) is None


def test_load_reference_list_reads_the_bundled_known_servers_list():
    reference = load_reference_list("known_servers.yaml")
    assert "@modelcontextprotocol/server-filesystem" in reference


def test_nearest_match_finds_a_one_edit_near_miss():
    reference = ("@modelcontextprotocol/server-filesystem",)
    assert nearest_match("@modelcontextprotocol/server-filesystme", reference, 2) == (
        "@modelcontextprotocol/server-filesystem",
        2,
    )


def test_nearest_match_excludes_exact_matches():
    reference = ("@modelcontextprotocol/server-filesystem",)
    assert nearest_match("@modelcontextprotocol/server-filesystem", reference, 2) is None


def test_nearest_match_excludes_names_too_far_away():
    reference = ("@modelcontextprotocol/server-filesystem",)
    assert nearest_match("completely-unrelated-package", reference, 2) is None


def test_nearest_match_returns_none_for_empty_reference():
    assert nearest_match("anything", (), 2) is None


def test_neighbors_of_finds_near_misses_sorted_by_distance_then_name():
    packages = [
        "@acme/server-filesystem",
        "@modelcontextprotocol/server-filesystemx",
        "@modelcontextprotocol/server-filesystem",  # exact match, excluded
        "totally-unrelated",
    ]
    result = neighbors_of("@modelcontextprotocol/server-filesystem", packages, max_distance=2)
    assert result == [("@modelcontextprotocol/server-filesystemx", 1)]


def test_neighbors_of_returns_empty_list_when_nothing_is_close():
    assert neighbors_of("@modelcontextprotocol/server-filesystem", ["totally-unrelated"], 2) == []


def test_typosquat_rule_config_finds_the_typosquat_rule():
    rules = [
        {"id": "MCP-STATIC-001", "detect": {"type": "regex"}},
        {
            "id": "MCP-STATIC-006",
            "detect": {
                "type": "typosquat",
                "reference_list": "known_servers.yaml",
                "max_distance": 2,
            },
        },
    ]
    assert typosquat_rule_config(rules) == ("known_servers.yaml", 2)


def test_typosquat_rule_config_returns_none_when_absent():
    rules = [{"id": "MCP-STATIC-001", "detect": {"type": "regex"}}]
    assert typosquat_rule_config(rules) is None

from __future__ import annotations

from mcphound.models import ServerConfig
from mcphound.policy import AllowedServer, Policy, check_allowlist, check_registries


def _server(command, name="test", transport="stdio", url=None) -> ServerConfig:
    return ServerConfig(name=name, transport=transport, command=command, url=url)


def test_check_allowlist_flags_unlisted_server():
    policy = Policy(servers=[])
    violations = check_allowlist([_server(["npx", "-y", "@acme/tool@1.0.0"])], policy)
    assert len(violations) == 1
    assert violations[0].kind == "unlisted_server"
    assert violations[0].server == "@acme/tool"


def test_check_allowlist_passes_matching_server():
    policy = Policy(servers=[AllowedServer(name="@acme/tool", version="1.0.0")])
    violations = check_allowlist([_server(["npx", "-y", "@acme/tool@1.0.0"])], policy)
    assert violations == []


def test_check_allowlist_flags_version_drift():
    policy = Policy(servers=[AllowedServer(name="@acme/tool", version="1.0.0")])
    violations = check_allowlist([_server(["npx", "-y", "@acme/tool@2.0.0"])], policy)
    assert len(violations) == 1
    assert violations[0].kind == "version_drift"


def test_check_allowlist_flags_digest_drift():
    old_digest = "sha256:" + "a" * 64
    new_digest = "sha256:" + "b" * 64
    policy = Policy(servers=[AllowedServer(name="ghcr.io/acme/tool", digest=old_digest)])
    violations = check_allowlist(
        [_server(["docker", "run", f"ghcr.io/acme/tool@{new_digest}"])], policy
    )
    assert len(violations) == 1
    assert violations[0].kind == "version_drift"


def test_check_registries_flags_blocked_match():
    policy = Policy(blocked_registries=["shady-mirror.example.com"])
    violations = check_registries(
        [_server(["docker", "run", "shady-mirror.example.com/acme/tool:1.0.0"])], policy
    )
    assert len(violations) == 1
    assert violations[0].kind == "blocked_registry"


def test_check_registries_passes_when_no_match():
    policy = Policy(blocked_registries=["shady-mirror.example.com"])
    violations = check_registries([_server(["npx", "-y", "@acme/tool@1.0.0"])], policy)
    assert violations == []

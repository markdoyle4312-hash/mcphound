from __future__ import annotations

from mcphound.models import ServerConfig
from mcphound.policy import resolved_digest, resolved_version, server_identity


def _server(command=None, transport="stdio", url=None, name="test") -> ServerConfig:
    return ServerConfig(name=name, transport=transport, command=command or [], url=url)


def test_server_identity_from_npx_command():
    assert server_identity(_server(["npx", "-y", "@acme/tool@1.0.0"])) == "@acme/tool"


def test_server_identity_from_docker_tagged_image():
    ref = "ghcr.io/acme/tool:1.2.3"
    assert server_identity(_server(["docker", "run", ref])) == "ghcr.io/acme/tool"


def test_server_identity_from_docker_digest_image():
    digest = "sha256:" + "a" * 64
    ref = f"ghcr.io/acme/tool@{digest}"
    assert server_identity(_server(["docker", "run", ref])) == "ghcr.io/acme/tool"


def test_server_identity_from_http_url():
    server = _server(transport="http", url="https://mcp.example.com/sse")
    assert server_identity(server) == "mcp.example.com"


def test_server_identity_falls_back_to_server_name():
    assert server_identity(_server(command=["some-binary"], name="my-server")) == "my-server"


def test_resolved_version_from_npx_command():
    assert resolved_version(_server(["npx", "-y", "@acme/tool@1.0.0"])) == "1.0.0"


def test_resolved_version_none_when_unpinned():
    assert resolved_version(_server(["npx", "-y", "@acme/tool"])) is None


def test_resolved_version_none_for_docker():
    assert resolved_version(_server(["docker", "run", "ghcr.io/acme/tool:1.2.3"])) is None


def test_resolved_digest_from_docker_digest_image():
    digest = "sha256:" + "a" * 64
    assert resolved_digest(_server(["docker", "run", f"ghcr.io/acme/tool@{digest}"])) == digest


def test_resolved_digest_none_for_tagged_image():
    assert resolved_digest(_server(["docker", "run", "ghcr.io/acme/tool:1.2.3"])) is None

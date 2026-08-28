from pathlib import Path

from mcpvet.discovery.clients import load_servers

FIXTURES = Path(__file__).parent / "fixtures"


def _config_fixture(name: str) -> Path:
    return FIXTURES / "configs" / name


def test_string_command_is_split_with_args():
    servers = load_servers(_config_fixture("claude_desktop.json"))
    assert servers[0].name == "claude-desktop-server"
    assert servers[0].command[0] == "npx"
    assert "@modelcontextprotocol/server-filesystem@1.0.0" in servers[0].command


def test_env_expansion_config_parses():
    servers = load_servers(_config_fixture("claude_desktop.json"))
    assert servers[0].env["MY_VAR"] == "value"


def test_cursor_config_parses():
    servers = load_servers(_config_fixture("cursor_mcp.json"))
    assert len(servers) == 1
    assert servers[0].name == "cursor-server"
    assert servers[0].command[0] == "uvx"
    assert "mcp-server-sqlite@0.1.0" in servers[0].command


def test_windsurf_config_parses():
    servers = load_servers(_config_fixture("windsurf_mcp_config.json"))
    assert len(servers) == 1
    assert servers[0].name == "windsurf-server"
    assert servers[0].command == ["python", "-m", "my_mcp_server", "--port", "8080"]


def test_gemini_config_parses():
    servers = load_servers(_config_fixture("gemini_mcp.json"))
    assert len(servers) == 1
    assert servers[0].name == "gemini-server"
    assert servers[0].command[0] == "npx"
    assert "@google/mcp-server@0.5.0" in servers[0].command


def test_opencode_shape_uses_mcp_key(tmp_path):
    cfg = tmp_path / "opencode.json"
    cfg.write_text(
        '{"mcp": {"ctx": {"type": "local", '
        '"command": ["npx", "-y", "@upstash/context7-mcp@1.0.0"]}}}'
    )
    servers = load_servers(cfg)
    assert len(servers) == 1
    assert servers[0].transport == "stdio"


def test_opencode_jsonc_with_comments(tmp_path):
    cfg = tmp_path / "opencode.jsonc"
    cfg.write_text(
        '{"mcp": {"ctx": {"type": "local", '
        '"command": ["npx", "-y", "@upstash/context7-mcp@1.0.0"]}}} // comment'
    )
    servers = load_servers(cfg)
    assert len(servers) == 1
    assert servers[0].transport == "stdio"


def test_opencode_jsonc_with_trailing_comma(tmp_path):
    cfg = tmp_path / "opencode.jsonc"
    cfg.write_text(
        '{"mcp": {"ctx": {"type": "local", '
        '"command": ["npx", "-y", "@upstash/context7-mcp@1.0.0"],}, }}'
    )
    servers = load_servers(cfg)
    assert len(servers) == 1
    assert servers[0].transport == "stdio"


def test_http_transport_detected_from_url():
    servers = load_servers(_config_fixture("claude_desktop.json"))
    servers[0].url = "https://example.com/mcp"
    servers[0].transport = "http"
    assert servers[0].transport == "http"


def test_disabled_server_is_skipped():
    cfg = FIXTURES / "configs" / "with_disabled.json"
    cfg.write_text(
        '{"mcpServers": {"enabled": {"command": "echo"}, '
        '"disabled": {"command": "echo", "enabled": false}}}'
    )
    servers = load_servers(cfg)
    assert len(servers) == 1
    assert servers[0].name == "enabled"
    cfg.unlink()

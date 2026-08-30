from mcphound.db.models import Server, Version
from mcphound.registry.adapter import version_to_server_config


def _version(**overrides):
    server = Server(name="io.github.acme/tool", raw_json={})
    defaults = dict(
        version="1.0.0",
        registry_type="npm",
        identifier="@acme/tool",
        transport="stdio",
        runtime_arguments=None,
        package_arguments=None,
        environment_variables=None,
        raw_json={"k": "v"},
    )
    defaults.update(overrides)
    version = Version(**defaults)
    version.server = server
    return version


def test_npm_version_synthesizes_pinned_npx_command():
    config = version_to_server_config(_version())
    assert config.command == ["npx", "-y", "@acme/tool@1.0.0"]
    assert config.transport == "stdio"
    assert config.name == "io.github.acme/tool"
    assert config.source == "registry:io.github.acme/tool@1.0.0"


def test_pypi_version_synthesizes_pinned_uvx_command():
    config = version_to_server_config(
        _version(registry_type="pypi", identifier="acme-tool", version="2.3.1")
    )
    assert config.command == ["uvx", "acme-tool@2.3.1"]


def test_oci_version_synthesizes_docker_run_command_without_pin():
    config = version_to_server_config(
        _version(registry_type="oci", identifier="ghcr.io/acme/tool:1.0.0")
    )
    assert config.command == ["docker", "run", "ghcr.io/acme/tool:1.0.0"]


def test_remote_version_has_no_command_and_sets_url():
    config = version_to_server_config(
        _version(
            registry_type="remote",
            identifier="https://acme.example/mcp",
            transport="http",
        )
    )
    assert config.command == []
    assert config.transport == "http"
    assert config.url == "https://acme.example/mcp"


def test_remote_version_still_carries_environment_variables():
    config = version_to_server_config(
        _version(
            registry_type="remote",
            identifier="https://acme.example/mcp",
            transport="http",
            environment_variables=[{"name": "API_KEY", "value": "sk-abcxyz1234567890"}],
        )
    )
    assert config.env == {"API_KEY": "sk-abcxyz1234567890"}


def test_package_arguments_are_appended_as_tokens_after_the_pinned_identifier():
    config = version_to_server_config(
        _version(package_arguments=[{"name": "--port", "value": "8080"}, "--verbose"])
    )
    assert config.command == ["npx", "-y", "@acme/tool@1.0.0", "--port", "8080", "--verbose"]


def test_runtime_arguments_come_before_package_arguments():
    config = version_to_server_config(
        _version(
            runtime_arguments=["--runtime-flag"],
            package_arguments=["--package-flag"],
        )
    )
    assert config.command == [
        "npx",
        "-y",
        "@acme/tool@1.0.0",
        "--runtime-flag",
        "--package-flag",
    ]


def test_environment_variables_list_shape_becomes_env_dict():
    config = version_to_server_config(
        _version(environment_variables=[{"name": "API_KEY", "value": "sk-abcxyz1234567890"}])
    )
    assert config.env == {"API_KEY": "sk-abcxyz1234567890"}


def test_environment_variables_dict_shape_is_also_accepted():
    config = version_to_server_config(_version(environment_variables={"API_KEY": "abc"}))
    assert config.env == {"API_KEY": "abc"}


def test_unrecognized_argument_shapes_yield_no_tokens_rather_than_guessing():
    config = version_to_server_config(_version(package_arguments={"not": "a list"}))
    assert config.command == ["npx", "-y", "@acme/tool@1.0.0"]

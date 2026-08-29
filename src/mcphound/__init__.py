"""mcphound — security scanner for MCP servers and agent skills."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("mcphound")
except PackageNotFoundError:
    # Running from a source checkout that was never `uv sync`/`pip install`-ed.
    __version__ = "0.0.0+unknown"

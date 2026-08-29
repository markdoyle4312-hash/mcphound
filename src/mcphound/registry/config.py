"""Load config/registry.yaml. Never holds a database URL or any other secret —
that always comes from the MCPHOUND_DATABASE_URL environment variable."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

DEFAULT_BASE_URL = "https://registry.modelcontextprotocol.io"
DEFAULT_PAGE_LIMIT = 100
DEFAULT_ARTIFACTS_DIR = "artifacts"


@dataclass
class RegistryPollConfig:
    base_url: str
    page_limit: int
    artifacts_dir: str


def load_config(path: Path) -> RegistryPollConfig:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    registry = data.get("registry") or {}
    return RegistryPollConfig(
        base_url=registry.get("base_url", DEFAULT_BASE_URL),
        page_limit=int(registry.get("page_limit", DEFAULT_PAGE_LIMIT)),
        artifacts_dir=registry.get("artifacts_dir", DEFAULT_ARTIFACTS_DIR),
    )

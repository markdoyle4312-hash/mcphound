"""Shared fixtures for DB-backed tests. Requires MCPHOUND_DATABASE_URL to point
at a real Postgres *_test database — these tests never run against SQLite or a
non-test database, and never mock the database itself (only the registry HTTP
call is mocked)."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config as AlembicConfig

from mcphound.db import session as db_session

REPO_ROOT = Path(__file__).resolve().parents[2]


def _require_test_database_url() -> str:
    url = os.environ.get("MCPHOUND_DATABASE_URL", "")
    if not url:
        pytest.skip("MCPHOUND_DATABASE_URL not set — see docs/registry-poller.md")
    if "test" not in url:
        pytest.skip(
            "MCPHOUND_DATABASE_URL must point at a *_test database to run DB-backed "
            "tests (refusing to run migrations against what looks like a dev database)."
        )
    return url


@pytest.fixture(scope="session", autouse=True)
def _migrated_test_db():
    _require_test_database_url()
    db_session.reset_engine()
    alembic_cfg = AlembicConfig(str(REPO_ROOT / "alembic.ini"))
    command.upgrade(alembic_cfg, "head")
    yield


@pytest.fixture
def db_session_fixture():
    factory = db_session.get_session_factory()
    session = factory()
    try:
        yield session
        session.rollback()
    finally:
        session.close()

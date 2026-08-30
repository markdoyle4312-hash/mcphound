"""Shared fixtures for DB-backed tests, used by tests/db/ and tests/api/.
Not a conftest.py itself — each directory's conftest.py re-exports the
names it needs, so these fixtures stay opt-in per-directory rather than
becoming globally autouse (most of the suite has no DB dependency).
Requires MCPHOUND_DATABASE_URL to point at a real Postgres *_test
database — these tests never run against SQLite or a non-test database,
and never mock the database itself (only the registry HTTP call is
mocked, elsewhere)."""

from __future__ import annotations

import datetime as dt
import os
from pathlib import Path

import pytest
from alembic.config import Config as AlembicConfig

from alembic import command
from mcphound.db import session as db_session
from mcphound.db.models import Server, Version

REPO_ROOT = Path(__file__).resolve().parents[1]


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


@pytest.fixture(scope="session")
def _migrated_test_db():
    """Not autouse: only tests that actually touch the DB should pay for
    (or skip on) migrations. db_session_fixture below depends on this
    explicitly, so any test using db_session_fixture/seed_version/the API's
    client fixture gets it transitively — a test in the same directory that
    never requests those (e.g. tests/db/test_models.py, which only inspects
    SQLAlchemy metadata) runs unaffected by DB availability."""
    _require_test_database_url()
    db_session.reset_engine()
    alembic_cfg = AlembicConfig(str(REPO_ROOT / "alembic.ini"))
    command.upgrade(alembic_cfg, "head")
    yield


@pytest.fixture
def db_session_fixture(_migrated_test_db):
    factory = db_session.get_session_factory()
    session = factory()
    try:
        yield session
        session.rollback()
    finally:
        session.close()


@pytest.fixture
def seed_version(db_session_fixture):
    """Factory fixture: seed_version() -> (Server, Version), both flushed
    (have real ids) but not committed. Callers can override any Version
    column via kwargs, e.g. seed_version(registry_type="pypi")."""

    def _seed(
        *,
        server_name: str = "io.github.acme/tool",
        version: str = "1.0.0",
        registry_type: str = "npm",
        identifier: str = "@acme/tool",
        transport: str | None = "stdio",
        runtime_arguments=None,
        package_arguments=None,
        environment_variables=None,
        is_latest: bool = True,
        delisted_at=None,
    ) -> tuple[Server, Version]:
        now = dt.datetime.now(dt.UTC)
        server = db_session_fixture.query(Server).filter_by(name=server_name).one_or_none()
        if server is None:
            server = Server(
                name=server_name,
                raw_json={},
                first_seen_at=now,
                last_seen_at=now,
            )
            db_session_fixture.add(server)
            db_session_fixture.flush()
        ver = Version(
            server_id=server.id,
            version=version,
            registry_type=registry_type,
            identifier=identifier,
            transport=transport,
            runtime_arguments=runtime_arguments,
            package_arguments=package_arguments,
            environment_variables=environment_variables,
            is_latest=is_latest,
            raw_json={},
            first_seen_at=now,
            last_seen_at=now,
            delisted_at=delisted_at,
        )
        db_session_fixture.add(ver)
        db_session_fixture.flush()
        return server, ver

    return _seed

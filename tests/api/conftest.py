"""Re-exports the shared DB fixtures for tests/api/ (see tests/_db_fixtures.py
for why this is a re-export rather than a top-level autouse fixture), plus
a TestClient wired to use the test's own DB session instead of opening a
new one — so seeded-but-uncommitted data in db_session_fixture is visible
to requests made through the client."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from mcphound.api.app import app, get_db
from tests._db_fixtures import _migrated_test_db, db_session_fixture, seed_version  # noqa: F401


@pytest.fixture
def client(db_session_fixture):  # noqa: F811 -- pytest fixture injection, not a real redefinition
    app.dependency_overrides[get_db] = lambda: db_session_fixture
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()

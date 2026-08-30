"""Fixture definitions live in tests/_db_fixtures.py (shared with
tests/api/) — this file just makes them apply to everything under
tests/db/."""

from __future__ import annotations

from tests._db_fixtures import _migrated_test_db, db_session_fixture, seed_version  # noqa: F401

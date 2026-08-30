"""Tests for src/mcphound/db/session.py's env-var validation and engine
caching. Deliberately doesn't use the _db_fixtures machinery (it requires a
real MCPHOUND_DATABASE_URL) — these only construct a lazy SQLAlchemy Engine
object, which never opens a connection, so no live Postgres is needed."""

from __future__ import annotations

import pytest

from mcphound.db import session as db_session


def test_get_engine_raises_a_clear_error_when_database_url_unset(monkeypatch):
    monkeypatch.delenv("MCPHOUND_DATABASE_URL", raising=False)
    db_session.reset_engine()
    try:
        with pytest.raises(RuntimeError, match="MCPHOUND_DATABASE_URL is not set"):
            db_session.get_engine()
    finally:
        db_session.reset_engine()


def test_get_session_factory_raises_the_same_error_when_unset(monkeypatch):
    monkeypatch.delenv("MCPHOUND_DATABASE_URL", raising=False)
    db_session.reset_engine()
    try:
        with pytest.raises(RuntimeError, match="MCPHOUND_DATABASE_URL is not set"):
            db_session.get_session_factory()
    finally:
        db_session.reset_engine()


def test_get_engine_is_cached_across_calls(monkeypatch):
    monkeypatch.setenv("MCPHOUND_DATABASE_URL", "postgresql+psycopg://u:p@localhost/does-not-exist")
    db_session.reset_engine()
    try:
        first = db_session.get_engine()
        second = db_session.get_engine()
        assert first is second
    finally:
        db_session.reset_engine()


def test_reset_engine_forces_a_fresh_engine_on_next_call(monkeypatch):
    monkeypatch.setenv("MCPHOUND_DATABASE_URL", "postgresql+psycopg://u:p@localhost/does-not-exist")
    db_session.reset_engine()
    try:
        first = db_session.get_engine()
        db_session.reset_engine()
        second = db_session.get_engine()
        assert first is not second
    finally:
        db_session.reset_engine()

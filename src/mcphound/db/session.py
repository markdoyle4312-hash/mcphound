"""Engine/session management for the registry poller and Alembic.

The database URL always comes from MCPHOUND_DATABASE_URL — never a config file,
per CLAUDE.md's "never put secrets in config files" rule.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

_engine: Engine | None = None
_session_factory: sessionmaker[Session] | None = None


def _database_url() -> str:
    url = os.environ.get("MCPHOUND_DATABASE_URL")
    if not url:
        raise RuntimeError(
            "MCPHOUND_DATABASE_URL is not set. See docs/registry-poller.md for local setup."
        )
    return url


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        _engine = create_engine(_database_url(), future=True)
    return _engine


def get_session_factory() -> sessionmaker[Session]:
    global _session_factory
    if _session_factory is None:
        _session_factory = sessionmaker(bind=get_engine(), future=True, expire_on_commit=False)
    return _session_factory


def reset_engine() -> None:
    """Drop the cached engine/session factory so a changed MCPHOUND_DATABASE_URL
    takes effect. Used by tests that set the env var per-session."""
    global _engine, _session_factory
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _session_factory = None


@contextmanager
def session_scope() -> Iterator[Session]:
    factory = get_session_factory()
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

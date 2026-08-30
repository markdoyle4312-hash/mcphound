"""Read-only server lookups for the API, backed directly by Postgres — the
same source of truth registry-scan/registry-export read from. Slug
resolution deliberately reuses registry/artifacts.py's own helpers (rather
than reimplementing the escaping) so the API can never disagree with the
static site about what a given slug means, collisions included."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db.models import Server
from ..registry.artifacts import (
    _findings_for_server,
    _latest_score,
    _safe_filename,
    escape_name_component,
)


@dataclass
class ServerRecord:
    name: str
    slug: str
    score: int
    finding_count: int
    last_scanned_at: datetime
    findings: list[dict]


def _build_record(session: Session, server: Server, slug: str) -> ServerRecord | None:
    score_row = _latest_score(session, server.id)
    if score_row is None:
        return None
    return ServerRecord(
        name=server.name,
        slug=slug,
        score=score_row.score,
        finding_count=score_row.finding_count,
        last_scanned_at=score_row.computed_at,
        findings=_findings_for_server(session, server.id),
    )


def get_server_by_name(session: Session, name: str) -> ServerRecord | None:
    server = session.execute(select(Server).where(Server.name == name)).scalars().first()
    if server is None:
        return None
    return _build_record(session, server, escape_name_component(server.name))


def get_server_by_slug(session: Session, slug: str) -> ServerRecord | None:
    seen_lower: set[str] = set()
    for server in session.execute(select(Server).order_by(Server.name)).scalars():
        candidate = _safe_filename(server.name, seen_lower).removesuffix(".json")
        if candidate == slug:
            return _build_record(session, server, candidate)
    return None

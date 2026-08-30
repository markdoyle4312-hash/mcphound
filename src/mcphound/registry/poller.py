"""Page the official MCP Registry and upsert servers/versions/hashes into Postgres.

Caller controls the transaction — this module only issues statements on the
given SQLAlchemy Session; it never calls commit() or rollback() itself, so the
CLI layer decides whether a run is real or --dry-run.
"""

from __future__ import annotations

import datetime as dt
import logging
from dataclasses import dataclass

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from ..db.models import Hash, Server, Version
from .client import RegistryServerEntry, iter_servers

logger = logging.getLogger(__name__)

_POLL_PROGRESS_INTERVAL = 100


@dataclass
class PollSummary:
    servers_seen: int = 0
    versions_seen: int = 0
    servers_new: int = 0
    versions_new: int = 0
    hashes_added: int = 0
    servers_delisted: int = 0
    versions_delisted: int = 0
    servers_relisted: int = 0
    versions_relisted: int = 0

    def format(self) -> str:
        return (
            f"servers: {self.servers_seen} seen "
            f"({self.servers_new} new, {self.servers_delisted} delisted, "
            f"{self.servers_relisted} relisted); "
            f"versions: {self.versions_seen} seen "
            f"({self.versions_new} new, {self.versions_delisted} delisted, "
            f"{self.versions_relisted} relisted); "
            f"{self.hashes_added} new hash observation(s)"
        )


def _upsert_server(
    session: Session, entry: RegistryServerEntry, run_started_at: dt.datetime, summary: PollSummary
) -> int:
    stmt = (
        pg_insert(Server)
        .values(
            name=entry.name,
            title=entry.title,
            description=entry.description,
            website_url=entry.website_url,
            repository_url=entry.repository_url,
            repository_source=entry.repository_source,
            raw_json=entry.raw,
            first_seen_at=run_started_at,
            last_seen_at=run_started_at,
            delisted_at=None,
        )
        .on_conflict_do_update(
            index_elements=[Server.name],
            set_={
                "title": entry.title,
                "description": entry.description,
                "website_url": entry.website_url,
                "repository_url": entry.repository_url,
                "repository_source": entry.repository_source,
                "raw_json": entry.raw,
                "last_seen_at": run_started_at,
                # delisted_at intentionally NOT reset here — _undelist_reappeared()
                # needs to see the pre-update value to detect and count a relist.
            },
        )
        .returning(Server.id, Server.first_seen_at)
    )
    row = session.execute(stmt).one()
    summary.servers_seen += 1
    if row.first_seen_at == run_started_at:
        summary.servers_new += 1
    return row.id


def _upsert_version(
    session: Session,
    server_id: int,
    entry: RegistryServerEntry,
    registry_type: str,
    identifier: str,
    transport: str | None,
    runtime_arguments,
    package_arguments,
    environment_variables,
    raw: dict,
    run_started_at: dt.datetime,
    summary: PollSummary,
) -> int:
    stmt = (
        pg_insert(Version)
        .values(
            server_id=server_id,
            version=entry.version,
            registry_type=registry_type,
            identifier=identifier,
            transport=transport,
            runtime_arguments=runtime_arguments,
            package_arguments=package_arguments,
            environment_variables=environment_variables,
            is_latest=entry.is_latest,
            status=entry.status,
            published_at=entry.published_at,
            raw_json=raw,
            first_seen_at=run_started_at,
            last_seen_at=run_started_at,
            delisted_at=None,
        )
        .on_conflict_do_update(
            constraint="uq_versions_natural_key",
            set_={
                "transport": transport,
                "runtime_arguments": runtime_arguments,
                "package_arguments": package_arguments,
                "environment_variables": environment_variables,
                "is_latest": entry.is_latest,
                "status": entry.status,
                "published_at": entry.published_at,
                "raw_json": raw,
                "last_seen_at": run_started_at,
                # delisted_at intentionally NOT reset here — _undelist_reappeared()
                # needs to see the pre-update value to detect and count a relist.
            },
        )
        .returning(Version.id, Version.first_seen_at)
    )
    row = session.execute(stmt).one()
    summary.versions_seen += 1
    if row.first_seen_at == run_started_at:
        summary.versions_new += 1
    return row.id


def _maybe_insert_hash(
    session: Session, version_id: int, sha256: str | None, summary: PollSummary
) -> None:
    if not sha256:
        return
    latest = session.execute(
        select(Hash.sha256)
        .where(Hash.version_id == version_id)
        .order_by(Hash.observed_at.desc())
        .limit(1)
    ).scalar_one_or_none()
    if latest == sha256:
        return
    session.add(Hash(version_id=version_id, sha256=sha256, source="registry"))
    summary.hashes_added += 1


def _mark_delisted(session: Session, run_started_at: dt.datetime, summary: PollSummary) -> None:
    result = session.execute(
        update(Server)
        .where(Server.last_seen_at < run_started_at, Server.delisted_at.is_(None))
        .values(delisted_at=run_started_at)
    )
    summary.servers_delisted = result.rowcount
    result = session.execute(
        update(Version)
        .where(Version.last_seen_at < run_started_at, Version.delisted_at.is_(None))
        .values(delisted_at=run_started_at)
    )
    summary.versions_delisted = result.rowcount


def _undelist_reappeared(
    session: Session,
    run_started_at: dt.datetime,
    summary: PollSummary,
) -> None:
    result = session.execute(
        update(Server)
        .where(Server.last_seen_at == run_started_at, Server.delisted_at.isnot(None))
        .values(delisted_at=None)
    )
    summary.servers_relisted = result.rowcount
    result = session.execute(
        update(Version)
        .where(Version.last_seen_at == run_started_at, Version.delisted_at.isnot(None))
        .values(delisted_at=None)
    )
    summary.versions_relisted = result.rowcount


def run_poll(session: Session, base_url: str, page_limit: int) -> PollSummary:
    """Page the full registry, upsert servers/versions/hashes, and mark-and-sweep
    anything no longer present. The caller commits or rolls back."""
    run_started_at = dt.datetime.now(dt.UTC)
    summary = PollSummary()

    for entry in iter_servers(base_url, page_limit):
        server_id = _upsert_server(session, entry, run_started_at, summary)
        if summary.servers_seen % _POLL_PROGRESS_INTERVAL == 0:
            logger.info("registry-poll: %d server(s) processed so far", summary.servers_seen)
        for pkg in entry.packages:
            version_id = _upsert_version(
                session,
                server_id,
                entry,
                registry_type=pkg.registry_type,
                identifier=pkg.identifier,
                transport=pkg.transport,
                runtime_arguments=pkg.runtime_arguments,
                package_arguments=pkg.package_arguments,
                environment_variables=pkg.environment_variables,
                raw=pkg.raw,
                run_started_at=run_started_at,
                summary=summary,
            )
            _maybe_insert_hash(session, version_id, pkg.file_sha256, summary)
        for remote in entry.remotes:
            _upsert_version(
                session,
                server_id,
                entry,
                registry_type="remote",
                identifier=remote.url,
                transport=remote.transport,
                runtime_arguments=None,
                package_arguments=None,
                environment_variables=None,
                raw=remote.raw,
                run_started_at=run_started_at,
                summary=summary,
            )

    _mark_delisted(session, run_started_at, summary)
    _undelist_reappeared(session, run_started_at, summary)
    session.flush()
    return summary

"""Batch-scan every currently-installable registry version: adapt each
Version row into a ServerConfig, run it through the existing rule engine,
and persist Scan/Finding rows.

Caller controls the transaction — same convention as registry/poller.py:
this module only issues statements on the given session, never commits or
rolls back."""

from __future__ import annotations

import datetime as dt
import logging
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db.models import Finding as FindingRow
from ..db.models import Hash, Scan, ServerScore, Version
from ..rules.engine import evaluate
from .adapter import version_to_server_config
from .scoring import dedupe_by_rule_id, score_server

logger = logging.getLogger(__name__)

# Batch size for IN(...) queries over version/scan ids. Keeps individual
# queries well clear of driver/parameter-count limits at registry scale
# (~25k in-scope versions) without needing an ids-as-array rewrite.
_IN_CLAUSE_BATCH_SIZE = 2000


def _chunked[T](items: list[T], size: int = _IN_CLAUSE_BATCH_SIZE) -> Iterator[list[T]]:
    for i in range(0, len(items), size):
        yield items[i : i + size]


_SCAN_PROGRESS_INTERVAL = 25

# evaluate() is I/O-bound (MCP-STATIC-007's npm registry lookup dominates), so a
# thread pool — not more processes — is the right tool; ~25k in-scope versions at
# one sequential network round-trip apiece is what blew the nightly job past
# GitHub Actions' 6h job limit.
# 16 ran the full registry (2026-08-31, run 33365883695) with zero HTTP 429s
# from registry.npmjs.org, so there was headroom left on the table; doubled to
# 32 to cut wall time further. _fetch_npm_metadata() still fails open with
# bounded 429 retries (engine.py) if this turns out to be too aggressive —
# revisit if a future run's logs show rate-limit backoffs kicking in.
DEFAULT_MAX_WORKERS = 32


@dataclass
class ScanSummary:
    versions_seen: int = 0
    versions_scanned: int = 0
    versions_skipped: int = 0
    versions_errored: int = 0
    findings_written: int = 0

    def format(self) -> str:
        return (
            f"versions: {self.versions_seen} in scope "
            f"({self.versions_scanned} scanned, {self.versions_skipped} skipped, "
            f"{self.versions_errored} errored); {self.findings_written} finding(s) written"
        )


def _in_scope_versions(session: Session) -> list[Version]:
    return list(
        session.execute(
            select(Version).where(Version.is_latest.is_(True), Version.delisted_at.is_(None))
        ).scalars()
    )


def _latest_hash_observed_map(
    session: Session, version_ids: list[int]
) -> dict[int, dt.datetime]:
    """version_id -> most recent Hash.observed_at, in one query per batch
    instead of one query per version (DISTINCT ON is Postgres-specific, same
    as the rest of this pipeline's use of pg_insert)."""
    result: dict[int, dt.datetime] = {}
    for batch in _chunked(version_ids):
        rows = session.execute(
            select(Hash.version_id, Hash.observed_at)
            .distinct(Hash.version_id)
            .where(Hash.version_id.in_(batch))
            .order_by(Hash.version_id, Hash.observed_at.desc())
        ).all()
        result.update({row.version_id: row.observed_at for row in rows})
    return result


def _latest_scan_at_map(
    session: Session, version_ids: list[int], mcphound_version: str
) -> dict[int, dt.datetime]:
    """version_id -> most recent Scan.scanned_at for this rule fingerprint."""
    result: dict[int, dt.datetime] = {}
    for batch in _chunked(version_ids):
        rows = session.execute(
            select(Scan.version_id, Scan.scanned_at)
            .distinct(Scan.version_id)
            .where(Scan.version_id.in_(batch), Scan.mcphound_version == mcphound_version)
            .order_by(Scan.version_id, Scan.scanned_at.desc())
        ).all()
        result.update({row.version_id: row.scanned_at for row in rows})
    return result


def _write_scan(session: Session, version_id: int, mcphound_version: str, findings, status: str):
    scan = Scan(version_id=version_id, mcphound_version=mcphound_version, deep=True, status=status)
    session.add(scan)
    session.flush()
    for f in findings:
        session.add(
            FindingRow(
                scan_id=scan.id,
                rule_id=f.rule_id,
                title=f.title,
                severity=f.severity,
                confidence=f.confidence,
                owasp=f.owasp,
                phase=f.phase,
                detail=f.detail,
                recommendation=f.recommendation,
            )
        )


def run_scan(
    session: Session,
    rules: list[dict],
    mcphound_version: str,
    max_workers: int = DEFAULT_MAX_WORKERS,
) -> ScanSummary:
    """No --deep filtering here (unlike the local `scan` command) — network-
    dependent rules (npm provenance) always run in the registry pipeline.

    Rule evaluation runs on a thread pool: `evaluate()` is pure/session-free
    (its only side effect is the npm HTTP call), so it's safe to fan out. Every
    session/ORM touch — reading `versions`, building each ServerConfig, writing
    `Scan`/`Finding` rows — stays on this thread only, since the SQLAlchemy
    Session isn't thread-safe."""
    versions = _in_scope_versions(session)
    total = len(versions)
    logger.info("registry-scan: %d version(s) in scope", total)
    summary = ScanSummary()
    processed = 0

    # Bulk-fetched once instead of two SELECTs per version — at registry
    # scale (~25k in-scope versions) the old per-version round trips to
    # Postgres dominated wall time before a single evaluate() call had run.
    version_ids = [v.id for v in versions]
    latest_scan_at = _latest_scan_at_map(session, version_ids, mcphound_version)
    latest_hash_at = _latest_hash_observed_map(session, version_ids)

    def _log_progress() -> None:
        if processed % _SCAN_PROGRESS_INTERVAL == 0 or processed == total:
            logger.info(
                "registry-scan: %d/%d versions processed (%d scanned, %d skipped, %d errored)",
                processed,
                total,
                summary.versions_scanned,
                summary.versions_skipped,
                summary.versions_errored,
            )

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {}
        for version in versions:
            summary.versions_seen += 1
            scanned_at = latest_scan_at.get(version.id)
            hash_at = latest_hash_at.get(version.id)
            needs_rescan = scanned_at is None or (hash_at is not None and hash_at > scanned_at)
            if not needs_rescan:
                summary.versions_skipped += 1
                processed += 1
                _log_progress()
                continue
            try:
                server_config = version_to_server_config(version)
            except Exception:
                logger.exception("registry-scan: failed to scan version_id=%s", version.id)
                _write_scan(session, version.id, mcphound_version, [], status="error")
                summary.versions_errored += 1
                processed += 1
                _log_progress()
                continue
            futures[executor.submit(evaluate, server_config, rules)] = version.id

        for future in as_completed(futures):
            version_id = futures[future]
            try:
                findings = future.result()
            except Exception:
                logger.exception("registry-scan: failed to scan version_id=%s", version_id)
                _write_scan(session, version_id, mcphound_version, [], status="error")
                summary.versions_errored += 1
            else:
                _write_scan(session, version_id, mcphound_version, findings, status="ok")
                summary.versions_scanned += 1
                summary.findings_written += len(findings)
            processed += 1
            _log_progress()

    session.flush()
    return summary


@dataclass
class ScoringSummary:
    servers_scored: int = 0

    def format(self) -> str:
        return f"servers scored: {self.servers_scored}"


def _in_scope_server_and_version_ids(session: Session) -> list[tuple[int, int]]:
    return list(
        session.execute(
            select(Version.server_id, Version.id).where(
                Version.is_latest.is_(True), Version.delisted_at.is_(None)
            )
        ).all()
    )


def _latest_ok_scan_id_map(session: Session, version_ids: list[int]) -> dict[int, int]:
    """version_id -> id of its most recent successful scan, one query per
    batch instead of one query per version."""
    result: dict[int, int] = {}
    for batch in _chunked(version_ids):
        rows = session.execute(
            select(Scan.version_id, Scan.id)
            .distinct(Scan.version_id)
            .where(Scan.version_id.in_(batch), Scan.status == "ok")
            .order_by(Scan.version_id, Scan.scanned_at.desc())
        ).all()
        result.update({row.version_id: row.id for row in rows})
    return result


def _findings_by_scan_id(session: Session, scan_ids: list[int]) -> dict[int, list[FindingRow]]:
    result: dict[int, list[FindingRow]] = {}
    for batch in _chunked(scan_ids):
        rows = session.execute(
            select(FindingRow).where(FindingRow.scan_id.in_(batch))
        ).scalars()
        for finding in rows:
            result.setdefault(finding.scan_id, []).append(finding)
    return result


def run_scoring(session: Session, mcphound_version: str) -> ScoringSummary:
    """Aggregates each server's in-scope versions' most recent successful
    scan into one unioned, de-duplicated finding set, scores it, and writes
    a ServerScore row. Independent of run_scan — can be re-run on its own
    (e.g. after tuning scoring.SEVERITY_WEIGHT) without rescanning.

    Batched into a handful of bulk queries rather than one query per
    server/version — at registry scale (~25k in-scope versions) the old
    per-version round trips to Postgres dominated wall time here just like
    in run_scan."""
    summary = ScoringSummary()
    server_and_version_ids = _in_scope_server_and_version_ids(session)
    version_ids_by_server: dict[int, list[int]] = {}
    for server_id, version_id in server_and_version_ids:
        version_ids_by_server.setdefault(server_id, []).append(version_id)

    all_version_ids = [version_id for _, version_id in server_and_version_ids]
    latest_scan_id = _latest_ok_scan_id_map(session, all_version_ids)
    findings_by_scan = _findings_by_scan_id(session, list(set(latest_scan_id.values())))

    for server_id, version_ids in version_ids_by_server.items():
        findings: list[FindingRow] = []
        for version_id in version_ids:
            scan_id = latest_scan_id.get(version_id)
            if scan_id is not None:
                findings.extend(findings_by_scan.get(scan_id, []))
        unioned = dedupe_by_rule_id(findings)
        session.add(
            ServerScore(
                server_id=server_id,
                score=score_server(unioned),
                finding_count=len(unioned),
                mcphound_version=mcphound_version,
            )
        )
        summary.servers_scored += 1
    session.flush()
    return summary

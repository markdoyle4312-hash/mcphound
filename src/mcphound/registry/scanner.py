"""Batch-scan every currently-installable registry version: adapt each
Version row into a ServerConfig, run it through the existing rule engine,
and persist Scan/Finding rows.

Caller controls the transaction — same convention as registry/poller.py:
this module only issues statements on the given session, never commits or
rolls back."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db.models import Finding as FindingRow
from ..db.models import Hash, Scan, ServerScore, Version
from ..rules.engine import evaluate
from .adapter import version_to_server_config
from .scoring import dedupe_by_rule_id, score_server

logger = logging.getLogger(__name__)

_SCAN_PROGRESS_INTERVAL = 25


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


def _latest_hash_observed_at(session: Session, version_id: int):
    return session.execute(
        select(Hash.observed_at)
        .where(Hash.version_id == version_id)
        .order_by(Hash.observed_at.desc())
        .limit(1)
    ).scalar_one_or_none()


def _needs_rescan(session: Session, version: Version, mcphound_version: str) -> bool:
    scan = (
        session.execute(
            select(Scan)
            .where(Scan.version_id == version.id, Scan.mcphound_version == mcphound_version)
            .order_by(Scan.scanned_at.desc())
            .limit(1)
        )
        .scalars()
        .first()
    )
    if scan is None:
        return True
    latest_hash_at = _latest_hash_observed_at(session, version.id)
    return latest_hash_at is not None and latest_hash_at > scan.scanned_at


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


def run_scan(session: Session, rules: list[dict], mcphound_version: str) -> ScanSummary:
    """No --deep filtering here (unlike the local `scan` command) — network-
    dependent rules (npm provenance) always run in the registry pipeline."""
    versions = _in_scope_versions(session)
    total = len(versions)
    logger.info("registry-scan: %d version(s) in scope", total)
    summary = ScanSummary()
    for version in versions:
        summary.versions_seen += 1
        if not _needs_rescan(session, version, mcphound_version):
            summary.versions_skipped += 1
        else:
            try:
                server_config = version_to_server_config(version)
                findings = evaluate(server_config, rules)
            except Exception:
                logger.exception("registry-scan: failed to scan version_id=%s", version.id)
                _write_scan(session, version.id, mcphound_version, [], status="error")
                summary.versions_errored += 1
            else:
                _write_scan(session, version.id, mcphound_version, findings, status="ok")
                summary.versions_scanned += 1
                summary.findings_written += len(findings)
        if summary.versions_seen % _SCAN_PROGRESS_INTERVAL == 0 or summary.versions_seen == total:
            logger.info(
                "registry-scan: %d/%d versions processed (%d scanned, %d skipped, %d errored)",
                summary.versions_seen,
                total,
                summary.versions_scanned,
                summary.versions_skipped,
                summary.versions_errored,
            )
    session.flush()
    return summary


@dataclass
class ScoringSummary:
    servers_scored: int = 0

    def format(self) -> str:
        return f"servers scored: {self.servers_scored}"


def _in_scope_server_ids(session: Session) -> list[int]:
    return list(
        session.execute(
            select(Version.server_id)
            .where(Version.is_latest.is_(True), Version.delisted_at.is_(None))
            .distinct()
        ).scalars()
    )


def _latest_ok_scan_findings(session: Session, version_id: int) -> list[FindingRow]:
    scan = (
        session.execute(
            select(Scan)
            .where(Scan.version_id == version_id, Scan.status == "ok")
            .order_by(Scan.scanned_at.desc())
            .limit(1)
        )
        .scalars()
        .first()
    )
    if scan is None:
        return []
    return list(session.execute(select(FindingRow).where(FindingRow.scan_id == scan.id)).scalars())


def run_scoring(session: Session, mcphound_version: str) -> ScoringSummary:
    """Aggregates each server's in-scope versions' most recent successful
    scan into one unioned, de-duplicated finding set, scores it, and writes
    a ServerScore row. Independent of run_scan — can be re-run on its own
    (e.g. after tuning scoring.SEVERITY_WEIGHT) without rescanning."""
    summary = ScoringSummary()
    for server_id in _in_scope_server_ids(session):
        version_ids = (
            session.execute(
                select(Version.id).where(
                    Version.server_id == server_id,
                    Version.is_latest.is_(True),
                    Version.delisted_at.is_(None),
                )
            )
            .scalars()
            .all()
        )
        findings: list[FindingRow] = []
        for version_id in version_ids:
            findings.extend(_latest_ok_scan_findings(session, version_id))
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

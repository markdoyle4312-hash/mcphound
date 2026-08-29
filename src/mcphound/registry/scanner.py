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
from ..db.models import Hash, Scan, Version
from ..rules.engine import evaluate
from .adapter import version_to_server_config

logger = logging.getLogger(__name__)


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
    summary = ScanSummary()
    for version in _in_scope_versions(session):
        summary.versions_seen += 1
        if not _needs_rescan(session, version, mcphound_version):
            summary.versions_skipped += 1
            continue
        try:
            server_config = version_to_server_config(version)
            findings = evaluate(server_config, rules)
        except Exception:
            logger.exception("registry-scan: failed to scan version_id=%s", version.id)
            _write_scan(session, version.id, mcphound_version, [], status="error")
            summary.versions_errored += 1
            continue
        _write_scan(session, version.id, mcphound_version, findings, status="ok")
        summary.versions_scanned += 1
        summary.findings_written += len(findings)
    session.flush()
    return summary

"""Write per-server JSON snapshots + a leaderboard index from committed
registry-scan results, for W14's static site generator to consume
directly (a directory of per-server files, not one combined file)."""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db.models import Finding as FindingRow
from ..db.models import Scan, Server, ServerScore, Version

logger = logging.getLogger(__name__)

_UNSAFE_NAME_CHARS = re.compile(r"[^A-Za-z0-9_.-]")


def _safe_filename(server_name: str) -> str:
    """Registry server names look like "io.github.foo/bar-server" — escape
    the slash first (so it reads as a name segment, not a path separator),
    then replace anything else filesystem-unsafe."""
    escaped = server_name.replace("/", "__")
    return _UNSAFE_NAME_CHARS.sub("_", escaped) + ".json"


def _latest_score(session: Session, server_id: int) -> ServerScore | None:
    return (
        session.execute(
            select(ServerScore)
            .where(ServerScore.server_id == server_id)
            .order_by(ServerScore.computed_at.desc())
            .limit(1)
        )
        .scalars()
        .first()
    )


def _findings_for_server(session: Session, server_id: int) -> list[dict]:
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
    findings: list[dict] = []
    for version_id in version_ids:
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
            continue
        rows = session.execute(select(FindingRow).where(FindingRow.scan_id == scan.id)).scalars()
        findings.extend(
            {
                "rule_id": row.rule_id,
                "title": row.title,
                "severity": row.severity,
                "confidence": row.confidence,
                "owasp": row.owasp,
                "detail": row.detail,
                "recommendation": row.recommendation,
            }
            for row in rows
        )
    return findings


def write_artifacts(session: Session, out_dir: Path) -> int:
    """Writes artifacts/servers/<name>.json + artifacts/index.json for every
    server with a computed score. One server's write failing (disk/
    permissions) is logged and skipped, never aborts the rest. Returns the
    number of servers successfully written."""
    servers_dir = out_dir / "servers"
    servers_dir.mkdir(parents=True, exist_ok=True)
    index: list[dict] = []
    written = 0
    for server in session.execute(select(Server)).scalars():
        score_row = _latest_score(session, server.id)
        if score_row is None:
            continue
        computed_at = score_row.computed_at.isoformat()
        payload = {
            "name": server.name,
            "score": score_row.score,
            "finding_count": score_row.finding_count,
            "computed_at": computed_at,
            "findings": _findings_for_server(session, server.id),
        }
        try:
            (servers_dir / _safe_filename(server.name)).write_text(
                json.dumps(payload, indent=2), encoding="utf-8"
            )
        except OSError:
            logger.warning("registry-scan: failed to write artifact for %s", server.name)
            continue
        index.append(
            {
                "name": server.name,
                "score": score_row.score,
                "finding_count": score_row.finding_count,
                "last_scanned_at": computed_at,
            }
        )
        written += 1
    (out_dir / "index.json").write_text(json.dumps(index, indent=2), encoding="utf-8")
    return written

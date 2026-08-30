"""Write per-server JSON snapshots + a leaderboard index from committed
registry-scan results, for W14's static site generator to consume
directly (a directory of per-server files, not one combined file)."""

from __future__ import annotations

import hashlib
import json
import logging
import re
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..db.models import Finding as FindingRow
from ..db.models import Scan, Server, ServerScore, Version
from ..rules.typosquat import (
    extract_command_package,
    load_reference_list,
    neighbors_of,
    typosquat_rule_config,
)
from .adapter import version_to_server_config

logger = logging.getLogger(__name__)

_UNSAFE_NAME_CHARS = re.compile(r"[^A-Za-z0-9_.@-]")


def escape_name_component(name: str) -> str:
    """Escape one registry name into filesystem-/URL-slug-safe form: '/'
    becomes '__' (so it reads as a name segment, not a path separator),
    everything else outside [A-Za-z0-9_.@-] becomes '_'. '@' is kept as-is
    since it's also reused for npm-scoped typosquat known-names
    (e.g. "@modelcontextprotocol/server-filesystem")."""
    escaped = name.replace("/", "__")
    return _UNSAFE_NAME_CHARS.sub("_", escaped)


def _safe_filename(server_name: str, seen_lower: set[str]) -> str:
    """Registry server names look like "io.github.foo/bar-server" — escape
    the slash first (so it reads as a name segment, not a path separator),
    then replace anything else filesystem-unsafe.

    Two real registry names differing only by case (e.g. "io.github.Foo/bar"
    vs "io.github.foo/bar") escape to filenames that collide on a
    case-insensitive filesystem (NTFS) even though they're distinct on
    case-sensitive ones (ext4, CI) — a second write would silently clobber
    the first with no error. `seen_lower` tracks lowercased names written so
    far in this run; a collision gets a short deterministic hash suffix
    instead of overwriting."""
    base = escape_name_component(server_name)
    key = base.lower()
    if key in seen_lower:
        base = f"{base}-{hashlib.sha1(server_name.encode()).hexdigest()[:8]}"
        key = base.lower()
    seen_lower.add(key)
    return base + ".json"


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
    seen_lower: set[str] = set()
    # Ordered by name so which of two case-colliding names gets the plain
    # filename (vs. the hash-suffixed one) is stable across runs.
    for server in session.execute(select(Server).order_by(Server.name)).scalars():
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
            filename = _safe_filename(server.name, seen_lower)
            (servers_dir / filename).write_text(json.dumps(payload, indent=2), encoding="utf-8")
        except OSError:
            logger.warning("registry-scan: failed to write artifact for %s", server.name)
            continue
        index.append(
            {
                "name": server.name,
                "slug": filename.removesuffix(".json"),
                "score": score_row.score,
                "finding_count": score_row.finding_count,
                "last_scanned_at": computed_at,
            }
        )
        written += 1
    (out_dir / "index.json").write_text(json.dumps(index, indent=2), encoding="utf-8")
    return written


def _candidate_packages(session: Session) -> list[tuple[str, str]]:
    """(server_name, package) for every current version whose launch command
    names an npm/pypi package the typosquat rule can compare — i.e. exactly
    the packages MCP-STATIC-006 would evaluate for that version."""
    versions = (
        session.execute(
            select(Version)
            .options(selectinload(Version.server))
            .where(Version.is_latest.is_(True), Version.delisted_at.is_(None))
        )
        .scalars()
        .all()
    )
    candidates: list[tuple[str, str]] = []
    for version in versions:
        pkg = extract_command_package(version_to_server_config(version))
        if pkg:
            candidates.append((version.server.name, pkg))
    return candidates


def write_typosquat_clusters(session: Session, out_dir: Path, rules: list[dict]) -> int:
    """Writes artifacts/typosquat-clusters.json: for every known-legitimate
    package name MCP-STATIC-006 compares against, every currently-listed
    registry package within its edit-distance threshold (excluding an exact
    match). Should run after write_artifacts() in the same out_dir — reads
    back index.json to attach each neighbor's site slug (None if that
    server has no score yet). Returns how many known names have at least
    one neighbor."""
    rule_config = typosquat_rule_config(rules)
    clusters: list[dict] = []
    clustered_count = 0
    if rule_config is not None:
        reference_list, max_distance = rule_config
        reference = load_reference_list(reference_list)
        candidates = _candidate_packages(session)
        pkg_to_server = {pkg: server_name for server_name, pkg in candidates}
        name_to_slug: dict[str, str] = {}
        index_path = out_dir / "index.json"
        if index_path.exists():
            rows = json.loads(index_path.read_text(encoding="utf-8"))
            name_to_slug = {row["name"]: row["slug"] for row in rows}
        for known_name in reference:
            neighbors = neighbors_of(known_name, pkg_to_server.keys(), max_distance)
            if neighbors:
                clustered_count += 1
            clusters.append(
                {
                    "known_name": known_name,
                    "known_slug": escape_name_component(known_name),
                    "neighbors": [
                        {
                            "identifier": pkg,
                            "distance": distance,
                            "server_name": pkg_to_server[pkg],
                            "server_slug": name_to_slug.get(pkg_to_server[pkg]),
                        }
                        for pkg, distance in neighbors
                    ],
                }
            )
    (out_dir / "typosquat-clusters.json").write_text(
        json.dumps(clusters, indent=2), encoding="utf-8"
    )
    return clustered_count


def write_all_artifacts(session: Session, out_dir: Path, rules: list[dict]) -> tuple[int, int]:
    """Runs the full artifact export: per-server files + leaderboard index,
    then typosquat clusters (which depend on index.json's slugs). Returns
    (servers_written, known_names_with_a_cluster)."""
    written = write_artifacts(session, out_dir)
    clustered = write_typosquat_clusters(session, out_dir, rules)
    return written, clustered

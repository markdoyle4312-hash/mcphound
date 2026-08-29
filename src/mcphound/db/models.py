"""SQLAlchemy declarative models for the registry poller's Postgres schema.

Table grain notes (see docs/registry-poller.md for the full rationale):
- `versions` is one row per server x version x (package-or-remote) — a server
  publishing both an npm package and a hosted remote for the same version gets
  two rows.
- `hashes` is append-only: a new row only when a version's sha256 changes.
- `scans`/`findings` are created here but populated by a later scanning pipeline,
  not the poller.
"""

from __future__ import annotations

import datetime as dt

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Server(Base, TimestampMixin):
    __tablename__ = "servers"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    title: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    website_url: Mapped[str | None] = mapped_column(Text)
    repository_url: Mapped[str | None] = mapped_column(Text)
    repository_source: Mapped[str | None] = mapped_column(Text)
    raw_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    first_seen_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    delisted_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))

    versions: Mapped[list[Version]] = relationship(back_populates="server")


class Version(Base, TimestampMixin):
    __tablename__ = "versions"
    __table_args__ = (
        UniqueConstraint(
            "server_id", "version", "registry_type", "identifier", name="uq_versions_natural_key"
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    server_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("servers.id"), nullable=False)
    version: Mapped[str] = mapped_column(String, nullable=False)
    registry_type: Mapped[str] = mapped_column(String, nullable=False)
    identifier: Mapped[str] = mapped_column(Text, nullable=False)
    transport: Mapped[str | None] = mapped_column(String)
    runtime_arguments: Mapped[dict | None] = mapped_column(JSONB)
    package_arguments: Mapped[dict | None] = mapped_column(JSONB)
    environment_variables: Mapped[dict | None] = mapped_column(JSONB)
    is_latest: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status: Mapped[str | None] = mapped_column(String)
    published_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    raw_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    first_seen_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    delisted_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))

    server: Mapped[Server] = relationship(back_populates="versions")
    hashes: Mapped[list[Hash]] = relationship(back_populates="version", order_by="Hash.observed_at")


class Hash(Base):
    __tablename__ = "hashes"
    __table_args__ = (Index("ix_hashes_version_observed", "version_id", "observed_at"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    version_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("versions.id"), nullable=False)
    sha256: Mapped[str] = mapped_column(String, nullable=False)
    source: Mapped[str] = mapped_column(String, nullable=False, server_default="registry")
    observed_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    version: Mapped[Version] = relationship(back_populates="hashes")


class Scan(Base):
    __tablename__ = "scans"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    version_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("versions.id"), nullable=False)
    scanned_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    mcphound_version: Mapped[str] = mapped_column(String, nullable=False)
    deep: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status: Mapped[str] = mapped_column(String, nullable=False)

    findings: Mapped[list[Finding]] = relationship(back_populates="scan")


class Finding(Base):
    __tablename__ = "findings"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    scan_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("scans.id"), nullable=False)
    rule_id: Mapped[str] = mapped_column(String, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(String, nullable=False)
    confidence: Mapped[str] = mapped_column(String, nullable=False)
    owasp: Mapped[str | None] = mapped_column(String)
    phase: Mapped[str] = mapped_column(String, nullable=False, default="static")
    detail: Mapped[str | None] = mapped_column(Text)
    recommendation: Mapped[str | None] = mapped_column(Text)

    scan: Mapped[Scan] = relationship(back_populates="findings")


class ServerScore(Base):
    """One row per scoring run — append-only, mirrors the `hashes` ledger
    style, so a server's score history is queryable without recomputing it."""

    __tablename__ = "server_scores"
    __table_args__ = (Index("ix_server_scores_server_computed", "server_id", "computed_at"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    server_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("servers.id"), nullable=False)
    computed_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    finding_count: Mapped[int] = mapped_column(Integer, nullable=False)
    mcphound_version: Mapped[str] = mapped_column(String, nullable=False)

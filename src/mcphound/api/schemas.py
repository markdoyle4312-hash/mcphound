"""Pydantic response models for the read-only API (W15). No behavior — the
route handlers in app.py map query results onto these explicitly."""

from __future__ import annotations

import datetime as dt

from pydantic import BaseModel


class Finding(BaseModel):
    rule_id: str
    title: str
    severity: str
    confidence: str
    owasp: str | None
    detail: str | None
    recommendation: str | None


class ServerDetail(BaseModel):
    name: str
    slug: str
    score: int
    finding_count: int
    last_scanned_at: dt.datetime
    findings: list[Finding]


class CheckResult(BaseModel):
    found: bool
    name: str
    slug: str | None = None
    score: int | None = None
    finding_count: int | None = None
    report_url: str | None = None

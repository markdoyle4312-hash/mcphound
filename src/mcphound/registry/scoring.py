"""Pure scoring functions — no DB or IO. Turns a server's findings into a
0-100 score via a multiplicative risk-decay model: each finding
independently scales down the *remaining* score, so one critical finding
alone can't zero out a server, but a pile of findings still compounds.

Accepts anything with .rule_id / .severity / .confidence attributes, so it
works equally with mcphound.models.Finding (pydantic, in-memory during a
scan) and mcphound.db.models.Finding (an already-persisted DB row) without
either module needing to import the other. Weight values are a tuning
knob, not load-bearing architecture — expected to be revisited after the
W16 manual spot-check sprint."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from ..models import SEVERITY_ORDER

SEVERITY_WEIGHT = {"critical": 0.55, "high": 0.35, "medium": 0.15, "low": 0.05}
CONFIDENCE_FACTOR = {"high": 1.0, "medium": 0.7, "low": 0.4}
_CONFIDENCE_ORDER = {"low": 1, "medium": 2, "high": 3}


class ScorableFinding(Protocol):
    rule_id: str
    severity: str
    confidence: str


def _decay(finding: ScorableFinding) -> float:
    weight = SEVERITY_WEIGHT.get(finding.severity, 0.0)
    factor = CONFIDENCE_FACTOR.get(finding.confidence, 0.0)
    return weight * factor


def score_server(findings: Sequence[ScorableFinding]) -> int:
    """0-100. Empty findings scores 100; more findings only ever decreases
    the score (monotonic non-increasing)."""
    score = 100.0
    for finding in findings:
        score *= 1 - _decay(finding)
    return max(0, min(100, round(score)))


def _rank(finding: ScorableFinding) -> tuple[int, int]:
    return (
        SEVERITY_ORDER.get(finding.severity, 0),
        _CONFIDENCE_ORDER.get(finding.confidence, 0),
    )


def dedupe_by_rule_id(findings: Sequence[ScorableFinding]) -> list[ScorableFinding]:
    """Union findings from a server's multiple in-scope versions, keeping
    the max (severity, confidence) pair per rule_id."""
    best: dict[str, ScorableFinding] = {}
    for finding in findings:
        current = best.get(finding.rule_id)
        if current is None or _rank(finding) > _rank(current):
            best[finding.rule_id] = finding
    return list(best.values())

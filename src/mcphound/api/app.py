"""Read-only FastAPI service over the registry-scan Postgres state (W15).
ASGI target for deployment: mcphound.api.app:app (e.g.
`uvicorn mcphound.api.app:app`). No write paths — see CLAUDE.md's
read-only rules for why this module never touches the DB except to
SELECT."""

from __future__ import annotations

import os
from collections.abc import Iterator

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

from ..db.session import get_session_factory
from .badge import render_badge
from .queries import get_server_by_name, get_server_by_slug
from .schemas import CheckResult, Finding, ServerDetail

SITE_BASE_URL = os.environ.get("MCPHOUND_SITE_BASE_URL", "https://mcphound.dev")

# Route-name -> slowapi limit string. A dict (not bare literals in the
# decorators) so tests can override one entry via monkeypatch.setitem
# without reconstructing the app; @limiter.limit() reads this dynamically
# via the lambdas below rather than a fixed string captured at import time.
RATE_LIMITS = {
    "servers": "60/minute",
    "check": "60/minute",
    "badge": "300/minute",
}

limiter = Limiter(key_func=get_remote_address)

app = FastAPI(title="mcphound API", version="1")
app.state.limiter = limiter
app.add_exception_handler(
    RateLimitExceeded,
    _rate_limit_exceeded_handler,  # type: ignore[arg-type]  # slowapi's handler is typed narrower than Starlette's
)


def get_db() -> Iterator[Session]:
    session = get_session_factory()()
    try:
        yield session
    finally:
        session.close()


def _to_server_detail(record) -> ServerDetail:
    return ServerDetail(
        name=record.name,
        slug=record.slug,
        score=record.score,
        finding_count=record.finding_count,
        last_scanned_at=record.last_scanned_at,
        findings=[Finding(**f) for f in record.findings],
    )


@app.get("/v1/servers/{slug}", response_model=ServerDetail)
@limiter.limit(lambda: RATE_LIMITS["servers"])
def read_server(slug: str, request: Request, db: Session = Depends(get_db)) -> ServerDetail:
    record = get_server_by_slug(db, slug)
    if record is None:
        raise HTTPException(status_code=404, detail="server not scored")
    return _to_server_detail(record)


@app.get("/v1/check", response_model=CheckResult)
@limiter.limit(lambda: RATE_LIMITS["check"])
def check_server(name: str, request: Request, db: Session = Depends(get_db)) -> CheckResult:
    record = get_server_by_name(db, name)
    if record is None:
        return CheckResult(found=False, name=name)
    return CheckResult(
        found=True,
        name=record.name,
        slug=record.slug,
        score=record.score,
        finding_count=record.finding_count,
        report_url=f"{SITE_BASE_URL}/servers/{record.slug}",
    )


@app.get("/v1/badge/{slug}.svg")
@limiter.limit(lambda: RATE_LIMITS["badge"])
def badge(slug: str, request: Request, db: Session = Depends(get_db)) -> Response:
    record = get_server_by_slug(db, slug)
    if record is None:
        raise HTTPException(status_code=404, detail="server not scored")
    svg = render_badge(record.score)
    return Response(
        content=svg,
        media_type="image/svg+xml",
        headers={"Cache-Control": "public, max-age=3600"},
    )

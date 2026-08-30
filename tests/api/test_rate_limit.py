from __future__ import annotations

from mcphound.api import app as app_module


def test_check_endpoint_is_rate_limited(client, monkeypatch):
    monkeypatch.setitem(app_module.RATE_LIMITS, "check", "2/minute")

    try:
        first = client.get("/v1/check", params={"name": "a"})
        second = client.get("/v1/check", params={"name": "a"})
        third = client.get("/v1/check", params={"name": "a"})
    finally:
        app_module.limiter.reset()

    assert first.status_code == 200
    assert second.status_code == 200
    assert third.status_code == 429

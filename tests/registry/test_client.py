from __future__ import annotations

import httpx
import pytest

from mcphound.registry import client

_PAGE_1 = {
    "servers": [
        {
            "server": {
                "name": "io.github.acme/tool",
                "version": "1.0.0",
                "description": "desc",
                "repository": {"url": "https://github.com/acme/tool", "source": "github"},
                "packages": [
                    {
                        "registryType": "npm",
                        "identifier": "@acme/tool",
                        "version": "1.0.0",
                        "transport": {"type": "stdio"},
                        "fileSha256": "abc123",
                    }
                ],
                "remotes": [],
            },
            "_meta": {
                "io.modelcontextprotocol.registry/official": {
                    "isLatest": True,
                    "status": "active",
                    "publishedAt": "2026-08-01T00:00:00Z",
                }
            },
        }
    ],
    "metadata": {"nextCursor": None},
}

_PAGE_1_WITH_CURSOR = {
    "servers": [
        {
            "server": {
                "name": "io.github.acme/tool",
                "version": "1.0.0",
                "description": "desc",
                "repository": {"url": "https://github.com/acme/tool", "source": "github"},
                "packages": [
                    {
                        "registryType": "npm",
                        "identifier": "@acme/tool",
                        "version": "1.0.0",
                        "transport": {"type": "stdio"},
                        "fileSha256": "abc123",
                    }
                ],
                "remotes": [],
            },
            "_meta": {
                "io.modelcontextprotocol.registry/official": {
                    "isLatest": True,
                    "status": "active",
                    "publishedAt": "2026-08-01T00:00:00Z",
                }
            },
        }
    ],
    "metadata": {"nextCursor": "page2"},
}

_PAGE_2 = {
    "servers": [
        {
            "server": {
                "name": "io.github.acme/other",
                "version": "2.0.0",
                "packages": [],
                "remotes": [{"url": "https://mcp.acme.dev/mcp", "type": "streamable-http"}],
            },
            "_meta": {},
        }
    ],
    "metadata": {"nextCursor": None},
}


def test_iter_servers_pages_until_empty_cursor(monkeypatch):
    pages = [_PAGE_1_WITH_CURSOR, _PAGE_2]
    calls: list[str | None] = []

    def fake_fetch(base_url, cursor, limit):
        calls.append(cursor)
        return pages[len(calls) - 1]

    monkeypatch.setattr(client, "_fetch_page", fake_fetch)

    entries = list(client.iter_servers("https://registry.example", page_limit=50))

    assert calls == [None, "page2"]
    assert [e.name for e in entries] == ["io.github.acme/tool", "io.github.acme/other"]


def test_iter_servers_parses_packages_and_meta(monkeypatch):
    monkeypatch.setattr(client, "_fetch_page", lambda base_url, cursor, limit: _PAGE_1)

    entries = list(client.iter_servers("https://registry.example"))

    pkg = entries[0].packages[0]
    assert pkg.identifier == "@acme/tool"
    assert pkg.file_sha256 == "abc123"
    assert pkg.registry_type == "npm"
    assert entries[0].is_latest is True
    assert entries[0].status == "active"
    assert entries[0].repository_url == "https://github.com/acme/tool"


def test_iter_servers_parses_remotes_and_missing_meta(monkeypatch):
    monkeypatch.setattr(client, "_fetch_page", lambda base_url, cursor, limit: _PAGE_2)

    entries = list(client.iter_servers("https://registry.example"))

    assert entries[0].remotes[0].url == "https://mcp.acme.dev/mcp"
    assert entries[0].remotes[0].transport == "streamable-http"
    assert entries[0].is_latest is False  # missing _meta defaults safely


def test_iter_servers_stops_on_single_page(monkeypatch):
    def fake_fetch(base_url, cursor, limit):
        assert cursor is None
        return {"servers": [], "metadata": {"nextCursor": None}}

    monkeypatch.setattr(client, "_fetch_page", fake_fetch)
    assert list(client.iter_servers("https://registry.example")) == []


def test_fetch_page_filters_to_latest_version(monkeypatch):
    captured = {}

    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {"servers": [], "metadata": {}}

    def fake_get(url, params, timeout):
        captured["params"] = params
        return FakeResponse()

    monkeypatch.setattr(client.httpx, "get", fake_get)

    client._fetch_page("https://registry.example", None, 50)

    assert captured["params"]["version"] == "latest"


_FAKE_REQUEST = httpx.Request("GET", "https://registry.example/v0.1/servers")


def test_fetch_page_retries_transient_timeout_then_succeeds(monkeypatch):
    monkeypatch.setattr(client.time, "sleep", lambda _: None)
    calls = {"n": 0}

    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {"servers": [], "metadata": {}}

    def fake_get(url, params, timeout):
        calls["n"] += 1
        if calls["n"] < 3:
            raise httpx.ReadTimeout("timed out")
        return FakeResponse()

    monkeypatch.setattr(client.httpx, "get", fake_get)

    result = client._fetch_page("https://registry.example", None, 50)

    assert result == {"servers": [], "metadata": {}}
    assert calls["n"] == 3


def test_fetch_page_gives_up_after_max_attempts(monkeypatch):
    monkeypatch.setattr(client.time, "sleep", lambda _: None)

    def fake_get(url, params, timeout):
        raise httpx.ReadTimeout("timed out")

    monkeypatch.setattr(client.httpx, "get", fake_get)

    with pytest.raises(httpx.ReadTimeout):
        client._fetch_page("https://registry.example", None, 50)


def test_fetch_page_does_not_retry_client_errors(monkeypatch):
    monkeypatch.setattr(client.time, "sleep", lambda _: None)
    calls = {"n": 0}

    class FakeResponse:
        status_code = 404

        def raise_for_status(self):
            raise httpx.HTTPStatusError("not found", request=_FAKE_REQUEST, response=self)

    def fake_get(url, params, timeout):
        calls["n"] += 1
        return FakeResponse()

    monkeypatch.setattr(client.httpx, "get", fake_get)

    with pytest.raises(httpx.HTTPStatusError):
        client._fetch_page("https://registry.example", None, 50)

    assert calls["n"] == 1


def test_fetch_page_retries_server_errors_then_succeeds(monkeypatch):
    monkeypatch.setattr(client.time, "sleep", lambda _: None)
    calls = {"n": 0}

    class FailResponse:
        status_code = 503

        def raise_for_status(self):
            raise httpx.HTTPStatusError("bad gateway", request=_FAKE_REQUEST, response=self)

    class OkResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {"servers": [], "metadata": {}}

    def fake_get(url, params, timeout):
        calls["n"] += 1
        return FailResponse() if calls["n"] < 2 else OkResponse()

    monkeypatch.setattr(client.httpx, "get", fake_get)

    result = client._fetch_page("https://registry.example", None, 50)

    assert result == {"servers": [], "metadata": {}}
    assert calls["n"] == 2

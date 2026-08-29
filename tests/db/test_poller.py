from __future__ import annotations

from mcphound.db.models import Hash, Server, Version
from mcphound.registry import client
from mcphound.registry.poller import run_poll

_ENTRY_PAGE = {
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
                        "fileSha256": "hash-v1",
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

_EMPTY_PAGE = {"servers": [], "metadata": {"nextCursor": None}}


def _page(page: dict):
    def fake_fetch(base_url, cursor, limit):
        return page

    return fake_fetch


def test_run_poll_inserts_server_version_and_hash(monkeypatch, db_session_fixture):
    monkeypatch.setattr(client, "_fetch_page", _page(_ENTRY_PAGE))

    summary = run_poll(db_session_fixture, "https://registry.example", 100)

    assert summary.servers_new == 1
    assert summary.versions_new == 1
    assert summary.hashes_added == 1

    server = db_session_fixture.query(Server).filter_by(name="io.github.acme/tool").one()
    version = db_session_fixture.query(Version).filter_by(server_id=server.id).one()
    hashes = db_session_fixture.query(Hash).filter_by(version_id=version.id).all()
    assert version.registry_type == "npm"
    assert version.identifier == "@acme/tool"
    assert [h.sha256 for h in hashes] == ["hash-v1"]


def test_run_poll_is_idempotent_and_dedupes_repeat_hash(monkeypatch, db_session_fixture):
    monkeypatch.setattr(client, "_fetch_page", _page(_ENTRY_PAGE))
    run_poll(db_session_fixture, "https://registry.example", 100)
    db_session_fixture.flush()

    summary = run_poll(db_session_fixture, "https://registry.example", 100)

    assert summary.servers_new == 0
    assert summary.versions_new == 0
    assert summary.hashes_added == 0

    server = db_session_fixture.query(Server).filter_by(name="io.github.acme/tool").one()
    assert db_session_fixture.query(Version).filter_by(server_id=server.id).count() == 1


def test_run_poll_records_new_hash_on_change(monkeypatch, db_session_fixture):
    monkeypatch.setattr(client, "_fetch_page", _page(_ENTRY_PAGE))
    run_poll(db_session_fixture, "https://registry.example", 100)
    db_session_fixture.flush()

    changed_page = {
        "servers": [
            {
                **_ENTRY_PAGE["servers"][0],
                "server": {
                    **_ENTRY_PAGE["servers"][0]["server"],
                    "packages": [
                        {
                            **_ENTRY_PAGE["servers"][0]["server"]["packages"][0],
                            "fileSha256": "hash-v2",
                        }
                    ],
                },
            }
        ],
        "metadata": {"nextCursor": None},
    }
    monkeypatch.setattr(client, "_fetch_page", _page(changed_page))

    summary = run_poll(db_session_fixture, "https://registry.example", 100)

    assert summary.hashes_added == 1
    server = db_session_fixture.query(Server).filter_by(name="io.github.acme/tool").one()
    version = db_session_fixture.query(Version).filter_by(server_id=server.id).one()
    hashes = (
        db_session_fixture.query(Hash)
        .filter_by(version_id=version.id)
        .order_by(Hash.observed_at)
        .all()
    )
    assert [h.sha256 for h in hashes] == ["hash-v1", "hash-v2"]


def test_run_poll_delists_servers_missing_from_next_run(monkeypatch, db_session_fixture):
    monkeypatch.setattr(client, "_fetch_page", _page(_ENTRY_PAGE))
    run_poll(db_session_fixture, "https://registry.example", 100)
    db_session_fixture.flush()

    monkeypatch.setattr(client, "_fetch_page", _page(_EMPTY_PAGE))
    summary = run_poll(db_session_fixture, "https://registry.example", 100)

    assert summary.servers_delisted == 1
    assert summary.versions_delisted == 1
    server = db_session_fixture.query(Server).filter_by(name="io.github.acme/tool").one()
    assert server.delisted_at is not None


def test_run_poll_relists_server_that_reappears(monkeypatch, db_session_fixture):
    monkeypatch.setattr(client, "_fetch_page", _page(_ENTRY_PAGE))
    run_poll(db_session_fixture, "https://registry.example", 100)
    db_session_fixture.flush()

    monkeypatch.setattr(client, "_fetch_page", _page(_EMPTY_PAGE))
    run_poll(db_session_fixture, "https://registry.example", 100)
    db_session_fixture.flush()

    monkeypatch.setattr(client, "_fetch_page", _page(_ENTRY_PAGE))
    summary = run_poll(db_session_fixture, "https://registry.example", 100)

    assert summary.servers_relisted == 1
    server = db_session_fixture.query(Server).filter_by(name="io.github.acme/tool").one()
    assert server.delisted_at is None

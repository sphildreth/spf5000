from __future__ import annotations

import threading
from pathlib import Path

import pytest

from app.core.config import settings
from app.db import connection

_TEST_SESSION_SECRET = "spf5000-test-session-secret-32bytes!!"


def _patch_settings(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    cache_dir = tmp_path / "cache"
    log_dir = tmp_path / "logs"

    monkeypatch.setattr(settings, "data_dir", data_dir)
    monkeypatch.setattr(settings, "cache_dir", cache_dir)
    monkeypatch.setattr(settings, "log_dir", log_dir)
    monkeypatch.setattr(settings, "database_path", data_dir / "spf5000.ddb")
    monkeypatch.setattr(settings, "frontend_dist_dir", tmp_path / "frontend-dist")
    monkeypatch.setattr(settings, "legacy_frontend_dist_dir", tmp_path / "frontend-dist-legacy")
    monkeypatch.setattr(settings, "session_secret", _TEST_SESSION_SECRET)


class _FakeConnection:
    def __init__(self, path: str) -> None:
        self.path = path
        self.closed = False
        self.commit_calls = 0
        self.rollback_calls = 0

    def commit(self) -> None:
        self.commit_calls += 1

    def rollback(self) -> None:
        self.rollback_calls += 1

    def close(self) -> None:
        self.closed = True


class _FakeDecentDb:
    def __init__(self) -> None:
        self.connections: list[_FakeConnection] = []

    def connect(self, path: str) -> _FakeConnection:
        conn = _FakeConnection(path)
        self.connections.append(conn)
        return conn


def test_runtime_connections_reuse_cached_connection_until_reset(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_settings(monkeypatch, tmp_path)
    fake_decentdb = _FakeDecentDb()

    connection.reset_connection_state()
    monkeypatch.setattr(connection, "decentdb", fake_decentdb)

    with connection.get_connection() as first:
        assert first._inner is fake_decentdb.connections[0]

    assert fake_decentdb.connections[0].commit_calls == 1
    assert fake_decentdb.connections[0].closed is False

    with connection.get_connection() as second:
        assert second._inner is fake_decentdb.connections[0]

    assert len(fake_decentdb.connections) == 1
    assert fake_decentdb.connections[0].commit_calls == 2
    assert fake_decentdb.connections[0].closed is False

    connection.reset_connection_state()
    assert fake_decentdb.connections[0].closed is True


def test_runtime_connections_do_not_accumulate_per_worker_thread(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_settings(monkeypatch, tmp_path)
    fake_decentdb = _FakeDecentDb()
    seen_connection_ids: list[int] = []
    seen_lock = threading.Lock()
    ready = threading.Barrier(4)

    connection.reset_connection_state()
    monkeypatch.setattr(connection, "decentdb", fake_decentdb)

    def use_connection_once() -> None:
        ready.wait()
        with connection.get_connection() as conn:
            with seen_lock:
                seen_connection_ids.append(id(conn._inner))

    threads = [threading.Thread(target=use_connection_once) for _ in range(4)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert len(fake_decentdb.connections) == 1
    assert len(set(seen_connection_ids)) == 1

    connection.reset_connection_state()
    assert fake_decentdb.connections[0].closed is True

from __future__ import annotations

from pathlib import Path

import decentdb
import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.db import bootstrap, connection
from app.db.connection import get_connection, is_null_connection
from app.main import create_app

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


def test_startup_recovers_from_unreadable_database_bootstrap_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_settings(monkeypatch, tmp_path)

    db_path = settings.database_path
    db_path.parent.mkdir(parents=True, exist_ok=True)
    db_path.write_bytes(b"unreadable-database")
    wal_path = Path(f"{db_path}-wal")
    wal_path.write_bytes(b"wal-bytes")
    shm_path = Path(f"{db_path}-shm")
    shm_path.write_bytes(b"shm-bytes")

    original_bootstrap_database = bootstrap.bootstrap_database
    attempts = {"count": 0}

    def flaky_bootstrap_database() -> None:
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise decentdb.DatabaseError("ERR_CORRUPTION: unreadable database header")
        original_bootstrap_database()

    monkeypatch.setattr(bootstrap, "bootstrap_database", flaky_bootstrap_database)
    app = create_app()
    with TestClient(app, raise_server_exceptions=True) as client:
        response = client.get("/api/health")
        assert response.status_code == 200

    assert attempts["count"] == 2
    assert db_path.exists()
    assert db_path.read_bytes() != b"unreadable-database"

    recovery_root = settings.staging_dir / "database-recovery"
    recovery_dirs = [path for path in recovery_root.iterdir() if path.is_dir()]
    assert len(recovery_dirs) == 1
    recovery_dir = recovery_dirs[0]
    assert (recovery_dir / db_path.name).read_bytes() == b"unreadable-database"
    assert (recovery_dir / wal_path.name).read_bytes().startswith(b"wal-bytes")
    assert (recovery_dir / shm_path.name).read_bytes().startswith(b"shm-bytes")

    with get_connection() as conn:
        assert not is_null_connection(conn)
        assert "settings" in set(conn.list_tables())


def test_initialize_runtime_reraises_nonrecoverable_database_errors(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_settings(monkeypatch, tmp_path)

    db_path = settings.database_path
    db_path.parent.mkdir(parents=True, exist_ok=True)
    db_path.write_bytes(b"existing-database")

    def broken_bootstrap_database() -> None:
        raise decentdb.ProgrammingError("Table not found")

    monkeypatch.setattr(bootstrap, "bootstrap_database", broken_bootstrap_database)

    with pytest.raises(decentdb.ProgrammingError):
        bootstrap.initialize_runtime()

    assert db_path.read_bytes() == b"existing-database"
    assert not (settings.staging_dir / "database-recovery").exists()


def test_request_time_open_failure_recovers_by_quarantining_database(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_settings(monkeypatch, tmp_path)

    app = create_app()
    with TestClient(app, raise_server_exceptions=True) as client:
        db_path = settings.database_path
        original_db_bytes = db_path.read_bytes()
        wal_path = Path(f"{db_path}-wal")
        wal_path.write_bytes(b"wal-bytes")
        shm_path = Path(f"{db_path}-shm")
        shm_path.write_bytes(b"shm-bytes")

        original_connect = connection.decentdb.connect
        attempts = {"count": 0}

        def flaky_connect(path: str):
            attempts["count"] += 1
            if attempts["count"] == 1:
                raise decentdb.OperationalError("Invalid page ID in WAL frame")
            return original_connect(path)

        monkeypatch.setattr(connection.decentdb, "connect", flaky_connect)

        response = client.get("/api/status")
        assert response.status_code == 401

        session_response = client.get("/api/auth/session")
        assert session_response.status_code == 200
        assert session_response.json() == {
            "auth_available": True,
            "bootstrapped": False,
            "authenticated": False,
            "user": None,
        }

    assert attempts["count"] >= 3
    assert db_path.exists()

    recovery_root = settings.staging_dir / "database-recovery"
    recovery_dirs = [path for path in recovery_root.iterdir() if path.is_dir()]
    assert len(recovery_dirs) == 1
    recovery_dir = recovery_dirs[0]
    assert (recovery_dir / db_path.name).read_bytes() == original_db_bytes
    assert (recovery_dir / wal_path.name).read_bytes().startswith(b"wal-bytes")
    assert (recovery_dir / shm_path.name).read_bytes().startswith(b"shm-bytes")

    with get_connection() as conn:
        assert not is_null_connection(conn)
        assert "settings" in set(conn.list_tables())

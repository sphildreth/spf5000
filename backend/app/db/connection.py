from __future__ import annotations

import threading
from contextlib import contextmanager
from typing import Any, Iterator

import structlog

from app.core.config import settings
from app.db.recovery import (
    existing_database_paths,
    is_recoverable_database_error,
    quarantine_unreadable_database,
)

try:
    import decentdb  # type: ignore
except Exception:  # pragma: no cover
    decentdb = None


class NullCursor:
    description: list[tuple[Any, ...]] = []

    def execute(self, *_args: Any, **_kwargs: Any) -> "NullCursor":
        return self

    def fetchone(self) -> Any:
        return None

    def fetchall(self) -> list[Any]:
        return []

    def close(self) -> None:
        return None


class NullConnection:
    is_null = True

    def cursor(self) -> NullCursor:
        return NullCursor()

    def execute(self, *_args: Any, **_kwargs: Any) -> NullCursor:
        return NullCursor()

    def commit(self) -> None:
        return None

    def rollback(self) -> None:
        return None

    def close(self) -> None:
        return None


def is_decentdb_available() -> bool:
    return decentdb is not None


def is_null_connection(conn: Any) -> bool:
    return bool(getattr(conn, "is_null", False))

_local = threading.local()
_connection_lock = threading.RLock()
_connection_generation = 0


LOGGER = structlog.get_logger(__name__)


def _statement_mutates(sql: Any) -> bool:
    if not isinstance(sql, str):
        return False

    statement = sql.lstrip().split(None, 1)
    if not statement:
        return False

    return statement[0].lower() in {
        "insert",
        "update",
        "delete",
        "replace",
        "create",
        "alter",
        "drop",
    }


class _TrackedConnection:
    def __init__(self, inner: Any) -> None:
        self._inner = inner
        self.dirty = False

    def execute(self, sql: Any, *args: Any, **kwargs: Any) -> Any:
        if _statement_mutates(sql):
            self.dirty = True
        return self._inner.execute(sql, *args, **kwargs)

    def commit(self) -> None:
        self._inner.commit()

    def rollback(self) -> None:
        self._inner.rollback()

    def close(self) -> None:
        self._inner.close()

    def __getattr__(self, name: str) -> Any:
        return getattr(self._inner, name)


def _close_thread_connection() -> None:
    conn_info = getattr(_local, "conn_info", None)
    if not conn_info:
        return

    conn = conn_info.get("conn")
    if conn is not None:
        try:
            conn.close()
        except Exception:
            pass
    _local.conn_info = None


@contextmanager
def exclusive_database_access() -> Iterator[None]:
    with _connection_lock:
        yield


def reset_connection_state() -> None:
    with _connection_lock:
        global _connection_generation
        _connection_generation += 1
        _close_thread_connection()
        if decentdb is not None:
            try:
                decentdb.evict_shared_wal(str(settings.database_path))
            except Exception:
                pass


def _recover_database_open_failure(exc: Exception) -> bool:
    if getattr(_local, "recovering_database_open", False):
        return False

    if not is_recoverable_database_error(exc):
        return False

    existing_paths = existing_database_paths()
    if not existing_paths:
        return False

    _local.recovering_database_open = True
    try:
        recovery_dir, moved_paths = quarantine_unreadable_database(
            reset_connection_state=reset_connection_state,
            exclusive_database_access=exclusive_database_access,
        )
        LOGGER.error(
            "decentdb_open_failed_corrupt",
            database_path=str(settings.database_path),
            moved_files=[path.name for path in moved_paths],
            recovery_dir=str(recovery_dir),
            exc_info=exc,
        )

        from app.db.bootstrap import bootstrap_database

        bootstrap_database()
        _close_thread_connection()
        LOGGER.warning(
            "decentdb_recovered_from_quarantine",
            recovery_dir=str(recovery_dir),
            trigger="request_open",
        )
        return True
    finally:
        _local.recovering_database_open = False


def _connect_with_recovery(db_path: str) -> Any:
    try:
        return decentdb.connect(db_path)
    except Exception as exc:
        if not _recover_database_open_failure(exc):
            raise
        return decentdb.connect(db_path)


def _get_thread_connection(db_path: str) -> Any:
    conn_info = getattr(_local, "conn_info", None)
    if conn_info:
        cached_path = conn_info.get("path")
        cached_conn = conn_info.get("conn")
        cached_gen = conn_info.get("gen")
        if cached_path == db_path and cached_conn is not None and cached_gen == _connection_generation:
            return cached_conn
        _close_thread_connection()

    conn = _TrackedConnection(_connect_with_recovery(db_path))
    _local.conn_info = {"conn": conn, "path": db_path, "gen": _connection_generation}
    return conn


@contextmanager
def get_connection() -> Iterator[Any]:
    with _connection_lock:
        settings.data_dir.mkdir(parents=True, exist_ok=True)
        settings.cache_dir.mkdir(parents=True, exist_ok=True)
        settings.log_dir.mkdir(parents=True, exist_ok=True)
        settings.database_path.parent.mkdir(parents=True, exist_ok=True)

        if decentdb is None:
            yield NullConnection()
            return

        db_path = str(settings.database_path)
        conn = _get_thread_connection(db_path)

        try:
            yield conn
            conn.commit()
            conn.dirty = False
        except Exception:
            try:
                conn.rollback()
            finally:
                _close_thread_connection()
            raise

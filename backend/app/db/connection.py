from __future__ import annotations

import threading
from contextlib import contextmanager
from typing import Any, Iterator

from app.core.config import settings

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


import sys

_is_test_env = "pytest" in sys.modules

_local = threading.local()
_connection_lock = threading.RLock()
_connection_generation = 0


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
    global _connection_generation

    with _connection_lock:
        _close_thread_connection()
        _connection_generation += 1


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

        if _is_test_env:
            conn = decentdb.connect(db_path)
            try:
                yield conn
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            finally:
                conn.close()
            return

        conn_info = getattr(_local, "conn_info", None)
        generation = _connection_generation

        if conn_info is None or conn_info["path"] != db_path or conn_info["generation"] != generation:
            _close_thread_connection()
            conn = decentdb.connect(db_path)
            _local.conn_info = {
                "conn": conn,
                "path": db_path,
                "depth": 0,
                "generation": generation,
            }
        else:
            conn = conn_info["conn"]

        _local.conn_info["depth"] += 1

        try:
            yield conn
            if _local.conn_info["depth"] == 1:
                conn.commit()
        except Exception:
            if _local.conn_info["depth"] == 1:
                conn.rollback()
            raise
        finally:
            _local.conn_info["depth"] -= 1

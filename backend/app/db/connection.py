from __future__ import annotations

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


@contextmanager
def get_connection() -> Iterator[Any]:
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    settings.cache_dir.mkdir(parents=True, exist_ok=True)
    settings.log_dir.mkdir(parents=True, exist_ok=True)
    settings.database_path.parent.mkdir(parents=True, exist_ok=True)

    if decentdb is None:
        conn = NullConnection()
    else:
        conn = decentdb.connect(str(settings.database_path))

    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

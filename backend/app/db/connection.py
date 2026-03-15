from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator, Any

from app.core.config import settings

try:
    import decentdb  # type: ignore
except Exception:  # pragma: no cover
    decentdb = None


class NullCursor:
    def execute(self, *_args: Any, **_kwargs: Any) -> None:
        return None

    def fetchone(self) -> dict[str, Any]:
        return {"ok": True}

    def fetchall(self) -> list[dict[str, Any]]:
        return []


class NullConnection:
    def cursor(self) -> NullCursor:
        return NullCursor()

    def commit(self) -> None:
        return None

    def rollback(self) -> None:
        return None

    def close(self) -> None:
        return None


@contextmanager
def get_connection() -> Iterator[Any]:
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    settings.cache_dir.mkdir(parents=True, exist_ok=True)

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

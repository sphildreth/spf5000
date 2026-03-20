from __future__ import annotations

from contextlib import AbstractContextManager
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from app.core.config import settings

try:
    import decentdb  # type: ignore
except Exception:  # pragma: no cover
    decentdb = None

_RECOVERABLE_DATABASE_ERROR_MARKERS = (
    '"native_code": 2',
    'err_corruption',
    'corrupt',
    'corruption',
    'not a database',
    'invalid page',
    'page id out of bounds',
    'checksum',
    'unreadable',
)


def is_recoverable_database_error(exc: Exception) -> bool:
    if decentdb is None or not isinstance(exc, decentdb.DatabaseError):
        return False

    message = str(exc).lower()
    return any(marker in message for marker in _RECOVERABLE_DATABASE_ERROR_MARKERS)


def existing_database_paths() -> list[Path]:
    candidates = [
        settings.database_path,
        Path(f'{settings.database_path}-wal'),
        Path(f'{settings.database_path}-shm'),
    ]
    return [path for path in candidates if path.exists()]


def quarantine_unreadable_database(
    *,
    reset_connection_state: Callable[[], None],
    exclusive_database_access: Callable[[], AbstractContextManager[None]],
) -> tuple[Path, list[Path]]:
    timestamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    recovery_dir = settings.staging_dir / 'database-recovery' / timestamp
    moved_paths: list[Path] = []

    with exclusive_database_access():
        reset_connection_state()
        recovery_dir.mkdir(parents=True, exist_ok=False)
        for source_path in existing_database_paths():
            target_path = recovery_dir / source_path.name
            source_path.replace(target_path)
            moved_paths.append(target_path)
        reset_connection_state()

    return recovery_dir, moved_paths

"""Database maintenance coordinator for SPF5000.

Runs periodic lightweight maintenance tasks (e.g., WAL checkpoint)
on a background thread.
"""

from __future__ import annotations

import structlog
import threading
import time

from app.core.config import settings
from app.db.connection import get_connection, is_null_connection, reset_connection_state
from app.db.recovery import database_paths

LOGGER = structlog.get_logger(__name__)

_DEFAULT_INTERVAL_SECONDS = 300
_DEFAULT_INITIAL_DELAY_SECONDS = 60
_DEFAULT_WAL_THRESHOLD_BYTES = 64 * 1024 * 1024
_MIN_INTERVAL_SECONDS = 60


class DatabaseMaintenanceCoordinator:
    """Periodically checkpoints the database to truncate WAL growth."""

    def __init__(
        self,
        *,
        interval_seconds: int | None = None,
        initial_delay_seconds: int | None = None,
        wal_threshold_bytes: int | None = None,
    ) -> None:
        self._interval_seconds = max(
            _MIN_INTERVAL_SECONDS,
            int(
                interval_seconds
                if interval_seconds is not None
                else settings.database_checkpoint_interval_seconds
            ),
        )
        self._initial_delay_seconds = max(
            0,
            int(
                initial_delay_seconds
                if initial_delay_seconds is not None
                else settings.database_checkpoint_initial_delay_seconds
            ),
        )
        self._wal_threshold_bytes = max(
            0,
            int(
                wal_threshold_bytes
                if wal_threshold_bytes is not None
                else settings.database_checkpoint_wal_threshold_bytes
            ),
        )
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._last_run_at: float | None = None
        self._last_skipped_at: float | None = None
        self._last_wal_size_bytes: int | None = None
        self._total_runs = 0
        self._total_skipped = 0

    def start(self) -> None:
        if self._thread is not None:
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run, name="db-maintenance", daemon=True
        )
        self._thread.start()
        LOGGER.info(
            "db_maintenance_started",
            interval_seconds=self._interval_seconds,
            initial_delay_seconds=self._initial_delay_seconds,
            wal_threshold_bytes=self._wal_threshold_bytes,
        )

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=5)
        self._thread = None
        LOGGER.info("db_maintenance_stopped")

    def get_status(self) -> dict:
        return {
            "thread_name": self._thread.name if self._thread else None,
            "is_running": self._thread is not None and self._thread.is_alive(),
            "last_run_at": self._last_run_at,
            "last_skipped_at": self._last_skipped_at,
            "last_wal_size_bytes": self._last_wal_size_bytes,
            "total_runs": self._total_runs,
            "total_skipped": self._total_skipped,
            "interval_seconds": self._interval_seconds,
            "initial_delay_seconds": self._initial_delay_seconds,
            "wal_threshold_bytes": self._wal_threshold_bytes,
        }

    def _run(self) -> None:
        if self._stop_event.wait(self._initial_delay_seconds):
            return

        while not self._stop_event.is_set():
            try:
                self._checkpoint_if_needed()
            except Exception as exc:
                LOGGER.warning("db_maintenance_checkpoint_failed", error=str(exc))
            if self._stop_event.wait(self._interval_seconds):
                return

    def _checkpoint_if_needed(self) -> None:
        wal_size = self._current_wal_size_bytes()
        self._last_wal_size_bytes = wal_size
        if self._wal_threshold_bytes > 0 and wal_size < self._wal_threshold_bytes:
            self._last_skipped_at = time.monotonic()
            self._total_skipped += 1
            LOGGER.debug(
                "db_maintenance_checkpoint_skipped",
                wal_size_bytes=wal_size,
                wal_threshold_bytes=self._wal_threshold_bytes,
            )
            return

        self._checkpoint()
        self._last_run_at = time.monotonic()
        self._total_runs += 1
        LOGGER.info(
            "db_maintenance_checkpoint_complete",
            wal_size_bytes=wal_size,
            wal_threshold_bytes=self._wal_threshold_bytes,
        )

    @staticmethod
    def _current_wal_size_bytes() -> int:
        wal_sizes = [
            path.stat().st_size
            for path in database_paths()[1:]
            if path.name.endswith(("wal", ".wal")) and path.exists()
        ]
        return max(wal_sizes, default=0)

    @staticmethod
    def _checkpoint() -> None:
        reset_connection_state()
        with get_connection() as conn:
            if is_null_connection(conn):
                LOGGER.warning("db_maintenance_null_connection")
                return
            conn.checkpoint()
        reset_connection_state()

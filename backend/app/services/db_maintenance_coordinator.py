"""Database maintenance coordinator for SPF5000.

Runs periodic lightweight maintenance tasks (e.g., WAL checkpoint)
on a background thread.
"""

from __future__ import annotations

import structlog
import threading
import time

from app.db.connection import get_connection, is_null_connection, reset_connection_state

LOGGER = structlog.get_logger(__name__)

_DEFAULT_INTERVAL_SECONDS = 86400  # 24 hours


class DatabaseMaintenanceCoordinator:
    """Periodically checkpoints the database to truncate WAL growth."""

    def __init__(self, *, interval_seconds: int = _DEFAULT_INTERVAL_SECONDS) -> None:
        self._interval_seconds = max(3600, interval_seconds)
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._last_run_at: float | None = None
        self._total_runs = 0

    def start(self) -> None:
        if self._thread is not None:
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run, name="db-maintenance", daemon=True
        )
        self._thread.start()
        LOGGER.info("db_maintenance_started", interval_seconds=self._interval_seconds)

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
            "total_runs": self._total_runs,
            "interval_seconds": self._interval_seconds,
        }

    def _run(self) -> None:
        # Wait the full interval before the first checkpoint so we don't
        # interfere with startup/recovery tests that manipulate WAL files.
        while not self._stop_event.wait(self._interval_seconds):
            try:
                self._checkpoint()
                self._last_run_at = time.monotonic()
                self._total_runs += 1
                LOGGER.info("db_maintenance_checkpoint_complete")
            except Exception as exc:
                LOGGER.warning("db_maintenance_checkpoint_failed", error=str(exc))

    @staticmethod
    def _checkpoint() -> None:
        reset_connection_state()
        with get_connection() as conn:
            if is_null_connection(conn):
                LOGGER.warning("db_maintenance_null_connection")
                return
            conn.checkpoint()
        reset_connection_state()

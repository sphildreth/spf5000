from __future__ import annotations

import structlog
import threading
from typing import Callable

from app.services.weather_service import WeatherService

LOGGER = structlog.get_logger(__name__)

_BASE_POLL_SECONDS = 30
_MAX_POLL_SECONDS = 3600


class WeatherSyncCoordinator:
    def __init__(
        self,
        service_factory: Callable[[], WeatherService],
        *,
        poll_seconds: int = _BASE_POLL_SECONDS,
    ) -> None:
        self._service_factory = service_factory
        self._poll_seconds = max(5, poll_seconds)
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._consecutive_failures = 0
        self._last_run_at: float | None = None
        self._last_run_trigger: str | None = None
        self._total_runs = 0
        self._total_failures = 0

    def start(self) -> None:
        if self._thread is not None:
            return
        self._thread = threading.Thread(
            target=self._run, name="weather-sync", daemon=True
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=5)
        self._thread = None

    def get_status(self) -> dict:
        """Return coordinator status for diagnostics."""
        return {
            "thread_name": self._thread.name if self._thread else None,
            "is_running": self._thread is not None and self._thread.is_alive(),
            "last_run_at": self._last_run_at,
            "last_run_trigger": self._last_run_trigger,
            "total_runs": self._total_runs,
            "total_failures": self._total_failures,
            "consecutive_failures": self._consecutive_failures,
            "poll_interval_seconds": self._poll_seconds,
        }

    def _run(self) -> None:
        import time
        consecutive_failures = 0
        while not self._stop_event.is_set():
            try:
                self._service_factory().refresh_due(trigger="scheduled")
                self._last_run_at = time.monotonic()
                self._last_run_trigger = "scheduled"
                self._total_runs += 1
                consecutive_failures = 0
                interval = self._poll_seconds
            except Exception:
                self._total_failures += 1
                consecutive_failures += 1
                interval = min(
                    self._poll_seconds * (2**consecutive_failures),
                    _MAX_POLL_SECONDS,
                )
                LOGGER.debug(
                    "weather_refresh_backing_off",
                    consecutive_failures=consecutive_failures,
                    interval_seconds=interval,
                )
            self._stop_event.wait(interval)

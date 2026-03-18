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

    def _run(self) -> None:
        consecutive_failures = 0
        while not self._stop_event.is_set():
            try:
                self._service_factory().refresh_due(trigger="scheduled")
                consecutive_failures = 0
                interval = self._poll_seconds
            except Exception:
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

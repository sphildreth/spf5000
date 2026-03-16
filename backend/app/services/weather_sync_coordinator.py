from __future__ import annotations

import logging
import threading
from typing import Callable

from app.services.weather_service import WeatherService

LOGGER = logging.getLogger(__name__)


class WeatherSyncCoordinator:
    def __init__(self, service_factory: Callable[[], WeatherService], *, poll_seconds: int = 30) -> None:
        self._service_factory = service_factory
        self._poll_seconds = max(5, poll_seconds)
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()

    def start(self) -> None:
        if self._thread is not None:
            return
        self._thread = threading.Thread(target=self._run, name="weather-sync", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=5)
        self._thread = None

    def _run(self) -> None:
        while not self._stop_event.is_set():
            try:
                self._service_factory().refresh_due(trigger="scheduled")
            except Exception:  # pragma: no cover
                LOGGER.exception("Scheduled weather refresh failed")
            self._stop_event.wait(self._poll_seconds)

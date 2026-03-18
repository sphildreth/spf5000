from __future__ import annotations

import logging
import structlog
import threading
import time
from collections import deque
from typing import Callable

from app.core.config import settings

LOGGER = structlog.get_logger(__name__)


class GooglePhotosSyncCoordinator:
    def __init__(self, service_factory: Callable[[], object]) -> None:
        self._service_factory = service_factory
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._wake_event = threading.Event()
        self._lock = threading.Lock()
        self._queued_triggers: deque[str] = deque()
        self._pending_set: set[str] = set()
        self._is_running = False
        self._last_trigger: str | None = None

    def start(self) -> None:
        if self._thread is not None:
            return
        self._thread = threading.Thread(
            target=self._run, name="google-photos-sync", daemon=True
        )
        self._thread.start()
        self.request_sync("startup")

    def stop(self) -> None:
        self._stop_event.set()
        self._wake_event.set()
        if self._thread is not None:
            self._thread.join(timeout=5)
        self._thread = None

    def request_sync(self, trigger: str = "manual") -> tuple[bool, bool]:
        with self._lock:
            already_queued = trigger in self._pending_set or (
                self._is_running and self._last_trigger == trigger
            )
            if not already_queued:
                self._queued_triggers.append(trigger)
                self._pending_set.add(trigger)
            self._wake_event.set()
        return (not already_queued, already_queued)

    def _run(self) -> None:
        next_periodic_deadline = time.monotonic() + max(
            1, settings.google_photos_sync_cadence_seconds
        )
        while not self._stop_event.is_set():
            timeout = max(0.0, next_periodic_deadline - time.monotonic())
            self._wake_event.wait(timeout)
            if self._stop_event.is_set():
                break

            trigger: str | None = None
            with self._lock:
                if self._queued_triggers:
                    trigger = self._queued_triggers.popleft()
                    self._pending_set.discard(trigger)
                elif time.monotonic() >= next_periodic_deadline:
                    trigger = "scheduled"
                if not self._queued_triggers:
                    self._wake_event.clear()

            if trigger is None:
                continue

            self._is_running = True
            self._last_trigger = trigger
            try:
                service = self._service_factory()
                service.run_sync(trigger=trigger)
            except Exception:  # pragma: no cover
                LOGGER.exception("google_photos_sync_failed", trigger=trigger)
            finally:
                self._is_running = False
                next_periodic_deadline = time.monotonic() + max(
                    1, settings.google_photos_sync_cadence_seconds
                )

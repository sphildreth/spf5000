from __future__ import annotations

import threading
import time
from typing import Any

import pytest

from app.services.google_photos_sync_coordinator import GooglePhotosSyncCoordinator
from app.services.weather_sync_coordinator import WeatherSyncCoordinator


class _FakeService:
    def __init__(self) -> None:
        self.sync_calls: list[str] = []
        self.raise_on_sync: Exception | None = None

    def run_sync(self, trigger: str) -> None:
        self.sync_calls.append(trigger)
        if self.raise_on_sync:
            raise self.raise_on_sync


class _SlowService:
    def __init__(self, ready: threading.Event, done: threading.Event) -> None:
        self.ready = ready
        self.done = done

    def run_sync(self, trigger: str) -> None:
        self.ready.set()
        self.done.wait(timeout=5)


class TestGooglePhotosSyncCoordinator:
    def test_start_stop_lifecycle(self) -> None:
        svc = _FakeService()
        coord = GooglePhotosSyncCoordinator(lambda: svc)
        coord.start()
        try:
            assert coord._thread is not None
            assert coord._thread.is_alive()
        finally:
            coord.stop()

    def test_stop_idempotent(self) -> None:
        coord = GooglePhotosSyncCoordinator(lambda: _FakeService())
        coord.start()
        coord.stop()
        coord.stop()

    def test_double_start_is_noop(self) -> None:
        svc = _FakeService()
        coord = GooglePhotosSyncCoordinator(lambda: svc)
        coord.start()
        coord.start()
        try:
            assert coord._thread is not None
            coord.stop()
        finally:
            coord.stop()

    def test_request_sync_queues_trigger(self) -> None:
        svc = _FakeService()
        coord = GooglePhotosSyncCoordinator(lambda: svc)
        coord.start()
        time.sleep(0.05)
        try:
            queued, already = coord.request_sync("manual")
            assert queued is True
            assert already is False
        finally:
            coord.stop()

    def test_request_sync_same_trigger_deduped(self) -> None:
        svc = _FakeService()
        coord = GooglePhotosSyncCoordinator(lambda: svc)
        coord.start()
        time.sleep(0.05)
        try:
            coord.request_sync("manual")
            time.sleep(0.01)
            queued, already = coord.request_sync("manual")
            assert queued is False
            assert already is True
        finally:
            coord.stop()

    def test_request_sync_different_triggers_both_queued(self) -> None:
        svc = _FakeService()
        coord = GooglePhotosSyncCoordinator(lambda: svc)
        coord.start()
        time.sleep(0.05)
        try:
            queued1, already1 = coord.request_sync("trigger-a")
            queued2, already2 = coord.request_sync("trigger-b")
            assert queued1 is True
            assert already1 is False
            assert queued2 is True
            assert already2 is False
        finally:
            coord.stop()

    def test_pending_set_tracks_triggers(self) -> None:
        svc = _FakeService()
        coord = GooglePhotosSyncCoordinator(lambda: svc)
        coord.start()
        time.sleep(0.05)
        try:
            coord.request_sync("deDupMe")
            time.sleep(0.01)
            assert "deDupMe" in coord._pending_set
            coord.request_sync("deDupMe")
            assert "deDupMe" in coord._pending_set
        finally:
            coord.stop()

    def test_pending_set_cleared_after_processing(self) -> None:
        svc = _FakeService()
        coord = GooglePhotosSyncCoordinator(lambda: svc)
        coord.start()
        time.sleep(0.05)
        try:
            coord.request_sync("one-shot")
            time.sleep(0.05)
            assert "one-shot" not in coord._pending_set
        finally:
            coord.stop()

    def test_concurrent_request_sync_no_duplicates(self) -> None:
        svc = _FakeService()
        coord = GooglePhotosSyncCoordinator(lambda: svc)
        coord.start()
        time.sleep(0.05)
        try:
            results: list[tuple[bool, bool]] = []

            def call_sync() -> None:
                results.append(coord.request_sync("concurrent"))

            threads = [threading.Thread(target=call_sync) for _ in range(5)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()

            queued_count = sum(1 for q, _ in results if q)
            assert queued_count == 1, (
                f"Expected 1 queued, got {queued_count} from {results}"
            )
        finally:
            coord.stop()

    def test_sync_exception_logged_not_raised(self) -> None:
        svc = _FakeService()
        svc.raise_on_sync = RuntimeError("sync failed")
        coord = GooglePhotosSyncCoordinator(lambda: svc)
        coord.start()
        time.sleep(0.05)
        try:
            coord.request_sync("error-trigger")
            time.sleep(0.1)
        finally:
            coord.stop()

    def test_request_sync_wakes_thread(self) -> None:
        svc = _FakeService()
        coord = GooglePhotosSyncCoordinator(lambda: svc)
        coord.start()
        time.sleep(0.05)
        try:
            time_before = time.monotonic()
            coord.request_sync("wake-test")
            time.sleep(0.1)
            time_after = time.monotonic()
            assert time_after - time_before < 2.0
        finally:
            coord.stop()


class _FakeWeatherService:
    def __init__(self, fail_count: int = 0) -> None:
        self.refresh_count = 0
        self.fail_count = fail_count
        self._fail_remaining = fail_count

    def refresh_due(self, trigger: str) -> None:
        self.refresh_count += 1
        if self._fail_remaining > 0:
            self._fail_remaining -= 1
            raise RuntimeError("forced refresh failure")


class TestWeatherSyncCoordinator:
    def test_start_stop_lifecycle(self) -> None:
        coord = WeatherSyncCoordinator(lambda: _FakeWeatherService(), poll_seconds=5)  # type: ignore[arg-type]
        coord.start()
        try:
            assert coord._thread is not None
            assert coord._thread.is_alive()
        finally:
            coord.stop()

    def test_stop_idempotent(self) -> None:
        coord = WeatherSyncCoordinator(lambda: _FakeWeatherService(), poll_seconds=5)  # type: ignore[arg-type]
        coord.start()
        coord.stop()
        coord.stop()

    def test_double_start_is_noop(self) -> None:
        coord = WeatherSyncCoordinator(lambda: _FakeWeatherService(), poll_seconds=5)  # type: ignore[arg-type]
        coord.start()
        coord.start()
        try:
            assert coord._thread is not None
            coord.stop()
        finally:
            coord.stop()

    def test_refresh_called_on_startup(self) -> None:
        svc = _FakeWeatherService()
        coord = WeatherSyncCoordinator(lambda: svc, poll_seconds=5)  # type: ignore[arg-type]
        coord.start()
        time.sleep(0.1)
        try:
            assert svc.refresh_count >= 1, "refresh should be called at startup"
        finally:
            coord.stop()

    def test_refresh_succeeds_resets_backoff(self) -> None:
        svc = _FakeWeatherService()
        coord = WeatherSyncCoordinator(lambda: svc, poll_seconds=5)  # type: ignore[arg-type]
        coord.start()
        time.sleep(0.1)
        try:
            assert svc.refresh_count >= 1
        finally:
            coord.stop()

    def test_refresh_failure_increments_failures(self) -> None:
        svc = _FakeWeatherService(fail_count=3)
        coord = WeatherSyncCoordinator(lambda: svc, poll_seconds=5)  # type: ignore[arg-type]
        coord.start()
        time.sleep(0.5)
        try:
            assert svc.refresh_count >= 1
        finally:
            coord.stop()

    def test_graceful_shutdown_on_stop(self) -> None:
        svc = _FakeWeatherService()
        coord = WeatherSyncCoordinator(lambda: svc, poll_seconds=5)  # type: ignore[arg-type]
        coord.start()
        time.sleep(0.05)
        coord.stop()
        assert coord._thread is None

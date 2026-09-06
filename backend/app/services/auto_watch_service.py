"""
Auto-watch service for SPF5000.

Watches the import directory for file changes and triggers scans automatically.
Uses the watchdog library for efficient file system monitoring.
"""

from __future__ import annotations

import threading
import time
from pathlib import Path
from typing import Callable

import structlog
from watchdog.observers import Observer
from watchdog.events import (
    FileSystemEventHandler,
    FileCreatedEvent,
    FileModifiedEvent,
    FileMovedEvent,
)

from app.core.config import settings
from app.repositories.settings_repository import SettingsRepository

LOGGER = structlog.get_logger(__name__)


class ImportDirectoryHandler(FileSystemEventHandler):
    """
    Handles file system events in the import directory.

    Debounces rapid file changes to avoid triggering multiple scans
    when files are being copied.
    """

    def __init__(
        self,
        scan_trigger: Callable[[], None],
        debounce_seconds: float = 5.0,
    ) -> None:
        super().__init__()
        self._scan_trigger = scan_trigger
        self._debounce_seconds = debounce_seconds
        self._pending_scan = False
        self._scan_timer: threading.Timer | None = None
        self._lock = threading.Lock()
        self._event_count = 0

    def on_created(self, event) -> None:
        """Handle file creation events."""
        if event.is_directory:
            return
        if self._is_image_file(event.src_path):
            self._schedule_scan()

    def on_modified(self, event) -> None:
        """Handle file modification events."""
        if event.is_directory:
            return
        if self._is_image_file(event.src_path):
            self._schedule_scan()

    def on_moved(self, event) -> None:
        """Handle file move events (file moved into directory)."""
        if event.is_directory:
            return
        if self._is_image_file(event.dest_path):
            self._schedule_scan()

    def _is_image_file(self, path: str) -> bool:
        """Check if the file is a supported image format."""
        supported_extensions = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".tiff", ".tif"}
        return Path(path).suffix.lower() in supported_extensions

    def _schedule_scan(self) -> None:
        """Schedule a scan after debounce period."""
        with self._lock:
            self._event_count += 1

            # Cancel existing timer
            if self._scan_timer is not None:
                self._scan_timer.cancel()

            # Schedule new scan
            self._pending_scan = True
            self._scan_timer = threading.Timer(
                self._debounce_seconds,
                self._trigger_scan,
            )
            self._scan_timer.start()

            LOGGER.debug(
                "import_file_detected",
                path=getattr(self, "_last_path", ""),
                events_buffered=self._event_count,
            )

    def _trigger_scan(self) -> None:
        """Trigger the scan after debounce period."""
        with self._lock:
            self._pending_scan = False
            events_count = self._event_count
            self._event_count = 0

        LOGGER.info("auto_watch_scan_triggered", events_detected=events_count)

        try:
            self._scan_trigger()
            LOGGER.info("auto_watch_scan_completed")
        except Exception as exc:
            LOGGER.error("auto_watch_scan_failed", error=str(exc))

    def stop(self) -> None:
        """Stop any pending scan."""
        with self._lock:
            if self._scan_timer is not None:
                self._scan_timer.cancel()
                self._scan_timer = None
            self._pending_scan = False
            self._event_count = 0


class AutoWatchService:
    """
    Watches the import directory for file changes and triggers scans.

    Runs in a background thread using the watchdog library for efficient
    file system monitoring.
    """

    def __init__(
        self,
        scan_trigger: Callable[[], None],
        settings_repo: SettingsRepository | None = None,
    ) -> None:
        self._scan_trigger = scan_trigger
        self._settings_repo = settings_repo or SettingsRepository()
        self._observer: Observer | None = None
        self._handler: ImportDirectoryHandler | None = None
        self._enabled: bool = False
        self._debounce_seconds: float = 5.0
        self._watch_path: Path = settings.local_import_dir
        self._last_scan_time: float | None = None
        self._events_detected: int = 0

    def start(self) -> None:
        """Start the file watcher."""
        self._load_settings()

        if not self._enabled:
            LOGGER.info("auto_watch_disabled")
            return

        if self._observer is not None:
            return

        # Ensure watch directory exists
        if not self._watch_path.exists():
            LOGGER.warning("auto_watch_directory_missing", path=str(self._watch_path))
            return

        self._handler = ImportDirectoryHandler(
            self._scan_trigger,
            debounce_seconds=self._debounce_seconds,
        )

        self._observer = Observer()
        self._observer.schedule(
            self._handler,
            str(self._watch_path),
            recursive=True,
        )
        self._observer.start()

        LOGGER.info(
            "auto_watch_started",
            path=str(self._watch_path),
            debounce_seconds=self._debounce_seconds,
        )

    def stop(self) -> None:
        """Stop the file watcher."""
        if self._handler:
            self._handler.stop()

        if self._observer:
            self._observer.stop()
            self._observer.join(timeout=5)

        self._observer = None
        self._handler = None

        LOGGER.info("auto_watch_stopped")

    def reload_settings(self) -> None:
        """Reload settings from database."""
        was_enabled = self._enabled
        self._load_settings()

        # Restart if enabled state changed
        if was_enabled and not self._enabled:
            self.stop()
        elif not was_enabled and self._enabled:
            self.stop()
            self.start()
        else:
            LOGGER.info("auto_watch_settings_reloaded", enabled=self._enabled)

    def get_status(self) -> dict:
        """Return current watcher status."""
        return {
            "enabled": self._enabled,
            "watch_path": str(self._watch_path),
            "debounce_seconds": self._debounce_seconds,
            "observer_alive": self._observer.is_alive() if self._observer else False,
            "last_scan": self._last_scan_time,
            "events_detected": self._events_detected,
        }

    def _load_settings(self) -> None:
        """Load auto-watch settings from database."""
        try:
            auto_watch_enabled = self._settings_repo.get_setting("auto_watch_enabled", "0")
            auto_watch_debounce = self._settings_repo.get_setting("auto_watch_debounce_seconds", "5")

            self._enabled = auto_watch_enabled == "1"
            self._debounce_seconds = float(auto_watch_debounce)
        except Exception as exc:
            LOGGER.warning("auto_watch_settings_load_failed", error=str(exc))
            self._enabled = False
            self._debounce_seconds = 5.0

"""
Auto-scan coordinator for SPF5000.

Manages both scheduled scans (cron-based) and file watching (watchdog-based)
for automatic import directory scanning.
"""

from __future__ import annotations

import structlog
from typing import Callable

from app.services.auto_scan_scheduler import AutoScanScheduler
from app.services.auto_watch_service import AutoWatchService
from app.repositories.settings_repository import SettingsRepository

LOGGER = structlog.get_logger(__name__)


class AutoScanCoordinator:
    """
    Coordinates automatic scanning of the import directory.
    
    Manages both:
    - Cron-based scheduled scans
    - File system watching for real-time change detection
    """
    
    def __init__(
        self,
        scan_trigger: Callable[[], None],
        settings_repo: SettingsRepository | None = None,
    ) -> None:
        self._scan_trigger = scan_trigger
        self._settings_repo = settings_repo or SettingsRepository()
        
        self._scheduler = AutoScanScheduler(
            scan_trigger=self._scan_trigger,
            settings_repo=self._settings_repo,
        )
        
        self._watcher = AutoWatchService(
            scan_trigger=self._scan_trigger,
            settings_repo=self._settings_repo,
        )
    
    def start(self) -> None:
        """Start both scheduler and watcher."""
        self._scheduler.start()
        self._watcher.start()
        LOGGER.info("auto_scan_coordinator_started")
    
    def stop(self) -> None:
        """Stop both scheduler and watcher."""
        self._scheduler.stop()
        self._watcher.stop()
        LOGGER.info("auto_scan_coordinator_stopped")
    
    def reload_settings(self) -> None:
        """Reload settings for both scheduler and watcher."""
        self._scheduler.reload_settings()
        self._watcher.reload_settings()
    
    def get_status(self) -> dict:
        """Return combined status of scheduler and watcher."""
        return {
            "scheduler": self._scheduler.get_status(),
            "watcher": self._watcher.get_status(),
        }

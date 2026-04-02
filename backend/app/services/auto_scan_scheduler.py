"""
Auto-scan scheduler service for SPF5000.

Provides cron-based scheduling for automatic import directory scanning.
"""

from __future__ import annotations

import threading
import time
from datetime import UTC, datetime
from typing import Callable

import structlog
from croniter import croniter

from app.core.config import settings
from app.repositories.settings_repository import SettingsRepository

LOGGER = structlog.get_logger(__name__)


class AutoScanScheduler:
    """
    Schedules automatic import directory scans based on cron expressions.
    
    Runs in a background thread and triggers scans according to the configured
    cron schedule.
    """
    
    def __init__(
        self,
        scan_trigger: Callable[[], None],
        settings_repo: SettingsRepository | None = None,
    ) -> None:
        self._scan_trigger = scan_trigger
        self._settings_repo = settings_repo or SettingsRepository()
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._last_scan_time: float | None = None
        self._next_run_time: datetime | None = None
        self._cron_schedule: str = ""
        self._enabled: bool = False
    
    def start(self) -> None:
        """Start the scheduler background thread."""
        if self._thread is not None:
            return
        
        self._stop_event.clear()
        self._load_settings()
        
        self._thread = threading.Thread(
            target=self._run,
            name="auto-scan-scheduler",
            daemon=True,
        )
        self._thread.start()
        LOGGER.info("auto_scan_scheduler_started", enabled=self._enabled, cron_schedule=self._cron_schedule)
    
    def stop(self) -> None:
        """Stop the scheduler background thread."""
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=5)
        self._thread = None
        LOGGER.info("auto_scan_scheduler_stopped")
    
    def reload_settings(self) -> None:
        """Reload settings from database (called when settings change)."""
        self._load_settings()
        LOGGER.info(
            "auto_scan_settings_reloaded",
            enabled=self._enabled,
            cron_schedule=self._cron_schedule,
        )
    
    def get_status(self) -> dict:
        """Return current scheduler status."""
        return {
            "enabled": self._enabled,
            "cron_schedule": self._cron_schedule,
            "next_run": self._next_run_time.isoformat() if self._next_run_time else None,
            "last_run": self._last_scan_time,
            "thread_alive": self._thread.is_alive() if self._thread else False,
        }
    
    def _load_settings(self) -> None:
        """Load auto-scan settings from database."""
        try:
            auto_scan_enabled = self._settings_repo.get_setting("auto_scan_enabled", "0")
            auto_scan_cron = self._settings_repo.get_setting("auto_scan_cron_schedule", "")
            
            self._enabled = auto_scan_enabled == "1"
            self._cron_schedule = auto_scan_cron.strip()
            
            if self._enabled and self._cron_schedule:
                self._calculate_next_run()
            else:
                self._next_run_time = None
        except Exception as exc:
            LOGGER.warning("auto_scan_settings_load_failed", error=str(exc))
            self._enabled = False
            self._cron_schedule = ""
            self._next_run_time = None
    
    def _calculate_next_run(self) -> None:
        """Calculate the next scheduled run time."""
        if not self._cron_schedule:
            self._next_run_time = None
            return
        
        try:
            cron = croniter(self._cron_schedule, datetime.now(UTC))
            self._next_run_time = cron.get_next(datetime)
        except Exception as exc:
            LOGGER.warning("auto_scan_cron_parse_failed", cron_schedule=self._cron_schedule, error=str(exc))
            self._next_run_time = None
    
    def _run(self) -> None:
        """Main scheduler loop."""
        while not self._stop_event.is_set():
            # Check if it's time to run
            if self._enabled and self._next_run_time:
                now = datetime.now(UTC)
                
                if now >= self._next_run_time:
                    self._trigger_scan()
                    self._calculate_next_run()
            
            # Sleep for a bit before checking again
            # Use shorter sleep when next run is soon
            sleep_seconds = 60  # Default: check every minute
            
            if self._next_run_time:
                time_until_run = (self._next_run_time - datetime.now(UTC)).total_seconds()
                if time_until_run > 0:
                    sleep_seconds = min(60, max(5, time_until_run))
                else:
                    sleep_seconds = 5
            
            self._stop_event.wait(sleep_seconds)
    
    def _trigger_scan(self) -> None:
        """Trigger an automatic scan."""
        self._last_scan_time = time.time()
        LOGGER.info("auto_scan_triggered", scheduled=True)
        
        try:
            self._scan_trigger()
            LOGGER.info("auto_scan_completed")
        except Exception as exc:
            LOGGER.error("auto_scan_failed", error=str(exc))

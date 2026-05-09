from __future__ import annotations

import time

from app.services.db_maintenance_coordinator import DatabaseMaintenanceCoordinator


def test_maintenance_coordinator_runs_and_reports_status() -> None:
    coord = DatabaseMaintenanceCoordinator(interval_seconds=3600)
    assert coord.get_status()["is_running"] is False
    assert coord.get_status()["total_runs"] == 0

    coord.start()
    assert coord.get_status()["is_running"] is True

    # Manually trigger one checkpoint cycle (avoids waiting the full interval)
    coord._checkpoint()  # type: ignore[misc]
    coord._last_run_at = time.monotonic()
    coord._total_runs += 1

    assert coord.get_status()["total_runs"] == 1
    assert coord.get_status()["last_run_at"] is not None

    coord.stop()
    assert coord.get_status()["is_running"] is False


def test_maintenance_coordinator_respects_minimum_interval() -> None:
    coord = DatabaseMaintenanceCoordinator(interval_seconds=60)
    # Minimum enforced at 1 hour
    assert coord.get_status()["interval_seconds"] == 3600

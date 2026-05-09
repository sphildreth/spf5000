from __future__ import annotations

from pathlib import Path

import pytest

from app.core.config import settings
from app.services.db_maintenance_coordinator import DatabaseMaintenanceCoordinator


def test_maintenance_coordinator_runs_and_reports_status() -> None:
    coord = DatabaseMaintenanceCoordinator(
        interval_seconds=3600,
        initial_delay_seconds=60,
        wal_threshold_bytes=0,
    )
    assert coord.get_status()["is_running"] is False
    assert coord.get_status()["total_runs"] == 0

    coord.start()
    assert coord.get_status()["is_running"] is True

    coord._checkpoint_if_needed()  # type: ignore[misc]

    assert coord.get_status()["total_runs"] == 1
    assert coord.get_status()["last_run_at"] is not None

    coord.stop()
    assert coord.get_status()["is_running"] is False


def test_maintenance_coordinator_respects_minimum_interval() -> None:
    coord = DatabaseMaintenanceCoordinator(interval_seconds=60)
    assert coord.get_status()["interval_seconds"] == 60


def test_maintenance_coordinator_skips_when_wal_below_threshold(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "database_path", tmp_path / "spf5000.ddb")
    Path(f"{settings.database_path}.wal").write_bytes(b"123456789")

    checkpoint_calls = 0

    def fake_checkpoint() -> None:
        nonlocal checkpoint_calls
        checkpoint_calls += 1

    coord = DatabaseMaintenanceCoordinator(
        interval_seconds=60,
        initial_delay_seconds=0,
        wal_threshold_bytes=10,
    )
    monkeypatch.setattr(coord, "_checkpoint", fake_checkpoint)

    coord._checkpoint_if_needed()  # type: ignore[misc]

    status = coord.get_status()
    assert checkpoint_calls == 0
    assert status["total_runs"] == 0
    assert status["total_skipped"] == 1
    assert status["last_wal_size_bytes"] == 9


def test_maintenance_coordinator_checkpoints_when_wal_reaches_threshold(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "database_path", tmp_path / "spf5000.ddb")
    Path(f"{settings.database_path}.wal").write_bytes(b"1234567890")

    checkpoint_calls = 0

    def fake_checkpoint() -> None:
        nonlocal checkpoint_calls
        checkpoint_calls += 1

    coord = DatabaseMaintenanceCoordinator(
        interval_seconds=60,
        initial_delay_seconds=0,
        wal_threshold_bytes=10,
    )
    monkeypatch.setattr(coord, "_checkpoint", fake_checkpoint)

    coord._checkpoint_if_needed()  # type: ignore[misc]

    status = coord.get_status()
    assert checkpoint_calls == 1
    assert status["total_runs"] == 1
    assert status["total_skipped"] == 0
    assert status["last_wal_size_bytes"] == 10

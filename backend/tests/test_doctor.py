from __future__ import annotations

from pathlib import Path
from typing import Generator

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import create_app
from app.models.sleep_schedule import SleepSchedule
from app.schemas.doctor import (
    DoctorResponse,
    HealthCheck,
    HealthCheckGroup,
    HealthSeverity,
)
from app.services.doctor_service import (
    ApplicationDoctorChecks,
    AuthDoctorChecks,
    BackupDoctorChecks,
    DatabaseDoctorChecks,
    DisplayDoctorChecks,
    DoctorService,
    MediaDoctorChecks,
    ProviderDoctorChecks,
    StorageDoctorChecks,
    WeatherDoctorChecks,
)


def _patch_settings(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    cache_dir = tmp_path / "cache"
    log_dir = tmp_path / "logs"

    monkeypatch.setattr(settings, "data_dir", data_dir)
    monkeypatch.setattr(settings, "cache_dir", cache_dir)
    monkeypatch.setattr(settings, "log_dir", log_dir)
    monkeypatch.setattr(settings, "database_path", data_dir / "spf5000.ddb")
    monkeypatch.setattr(settings, "frontend_dist_dir", tmp_path / "frontend-dist")
    monkeypatch.setattr(
        settings, "legacy_frontend_dist_dir", tmp_path / "frontend-dist-legacy"
    )
    monkeypatch.setattr(
        settings, "session_secret", "spf5000-test-session-secret-32bytes!!"
    )


class TestHealthCheckSeverityRollup:
    def test_all_ok_returns_ok(self) -> None:
        checks = [
            HealthCheck(id="a", title="A", severity=HealthSeverity.OK, summary=""),
            HealthCheck(id="b", title="B", severity=HealthSeverity.OK, summary=""),
        ]
        assert DoctorService._compute_group_status(checks) == HealthSeverity.OK

    def test_one_warning_returns_warning(self) -> None:
        checks = [
            HealthCheck(id="a", title="A", severity=HealthSeverity.OK, summary=""),
            HealthCheck(id="b", title="B", severity=HealthSeverity.WARNING, summary=""),
        ]
        assert DoctorService._compute_group_status(checks) == HealthSeverity.WARNING

    def test_one_error_returns_error(self) -> None:
        checks = [
            HealthCheck(id="a", title="A", severity=HealthSeverity.OK, summary=""),
            HealthCheck(id="b", title="B", severity=HealthSeverity.ERROR, summary=""),
        ]
        assert DoctorService._compute_group_status(checks) == HealthSeverity.ERROR

    def test_info_does_not_override_error_or_warning(self) -> None:
        checks = [
            HealthCheck(id="a", title="A", severity=HealthSeverity.INFO, summary=""),
            HealthCheck(id="b", title="B", severity=HealthSeverity.ERROR, summary=""),
        ]
        assert DoctorService._compute_group_status(checks) == HealthSeverity.ERROR


class TestDoctorResponseAggregation:
    def test_overall_status_all_ok(self) -> None:
        groups = [
            HealthCheckGroup(
                id="g1",
                title="G1",
                status=HealthSeverity.OK,
                checks=[
                    HealthCheck(
                        id="c1", title="C1", severity=HealthSeverity.OK, summary=""
                    ),
                ],
            ),
        ]
        response = DoctorResponse.from_groups(groups)
        assert response.overall_status == HealthSeverity.OK
        assert "passed" in response.summary.lower()

    def test_overall_status_with_error(self) -> None:
        groups = [
            HealthCheckGroup(
                id="g1",
                title="G1",
                status=HealthSeverity.OK,
                checks=[
                    HealthCheck(
                        id="c1", title="C1", severity=HealthSeverity.OK, summary=""
                    ),
                ],
            ),
            HealthCheckGroup(
                id="g2",
                title="G2",
                status=HealthSeverity.ERROR,
                checks=[
                    HealthCheck(
                        id="c2", title="C2", severity=HealthSeverity.ERROR, summary=""
                    ),
                ],
            ),
        ]
        response = DoctorResponse.from_groups(groups)
        assert response.overall_status == HealthSeverity.ERROR

    def test_overall_status_with_warning(self) -> None:
        groups = [
            HealthCheckGroup(
                id="g1",
                title="G1",
                status=HealthSeverity.OK,
                checks=[
                    HealthCheck(
                        id="c1", title="C1", severity=HealthSeverity.OK, summary=""
                    ),
                ],
            ),
            HealthCheckGroup(
                id="g2",
                title="G2",
                status=HealthSeverity.WARNING,
                checks=[
                    HealthCheck(
                        id="c2", title="C2", severity=HealthSeverity.WARNING, summary=""
                    ),
                ],
            ),
        ]
        response = DoctorResponse.from_groups(groups)
        assert response.overall_status == HealthSeverity.WARNING

    def test_response_has_timestamp(self) -> None:
        groups = [
            HealthCheckGroup(
                id="g1",
                title="G1",
                status=HealthSeverity.OK,
                checks=[],
            ),
        ]
        response = DoctorResponse.from_groups(groups)
        assert response.checked_at is not None
        assert len(response.checked_at) > 0


class TestDoctorService:
    def test_runs_all_checkers(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _patch_settings(monkeypatch, tmp_path)

        service = DoctorService()
        result = service.run_all_checks()

        assert result.overall_status in [
            HealthSeverity.OK,
            HealthSeverity.WARNING,
            HealthSeverity.ERROR,
        ]
        group_ids = {g.id for g in result.groups}
        expected_ids = {
            "application",
            "database",
            "storage",
            "auth",
            "media",
            "providers",
            "weather",
            "display",
            "backup",
        }
        assert group_ids == expected_ids

    def test_groups_have_checks(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _patch_settings(monkeypatch, tmp_path)

        service = DoctorService()
        result = service.run_all_checks()

        for group in result.groups:
            assert len(group.checks) > 0, f"Group {group.id} has no checks"
            for check in group.checks:
                assert check.id
                assert check.title
                assert check.summary
                assert check.severity in [
                    HealthSeverity.OK,
                    HealthSeverity.WARNING,
                    HealthSeverity.ERROR,
                    HealthSeverity.INFO,
                ]


class TestApplicationDoctorChecks:
    def test_returns_checks(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _patch_settings(monkeypatch, tmp_path)

        checks = ApplicationDoctorChecks.run()
        assert len(checks) >= 3

        ids = {c.id for c in checks}
        assert "app_reachable" in ids
        assert "app_version" in ids
        assert "system_time" in ids

        app_reachable = next((c for c in checks if c.id == "app_reachable"), None)
        assert app_reachable is not None
        assert app_reachable.severity == HealthSeverity.OK

    def test_version_check_is_info(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _patch_settings(monkeypatch, tmp_path)

        checks = ApplicationDoctorChecks.run()
        version_check = next((c for c in checks if c.id == "app_version"), None)
        assert version_check is not None
        assert version_check.severity == HealthSeverity.INFO


class TestDatabaseDoctorChecks:
    def test_database_file_check(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _patch_settings(monkeypatch, tmp_path)

        check = DatabaseDoctorChecks._check_file_exists()
        assert check.id == "database_file"
        assert check.severity in [HealthSeverity.OK, HealthSeverity.ERROR]


class TestStorageDoctorChecks:
    def test_data_dir_check(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _patch_settings(monkeypatch, tmp_path)

        checks = StorageDoctorChecks.run()
        assert len(checks) > 0

        data_dir_check = next((c for c in checks if c.id == "data_dir"), None)
        assert data_dir_check is not None
        assert data_dir_check.severity in [HealthSeverity.OK, HealthSeverity.WARNING]


class TestDisplayDoctorChecks:
    def test_sleep_schedule_reports_enabled_schedule(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            "app.repositories.settings_repository.SettingsRepository.get_sleep_schedule",
            lambda self: SleepSchedule(
                sleep_schedule_enabled=True,
                sleep_start_local_time="22:00",
                sleep_end_local_time="08:00",
            ),
        )

        check = DisplayDoctorChecks._check_sleep_schedule()

        assert check.severity == HealthSeverity.INFO
        assert check.summary == "Sleep schedule enabled (22:00 - 08:00)."

    def test_sleep_schedule_reports_disabled_schedule(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            "app.repositories.settings_repository.SettingsRepository.get_sleep_schedule",
            lambda self: SleepSchedule(
                sleep_schedule_enabled=False,
                sleep_start_local_time="22:00",
                sleep_end_local_time="08:00",
            ),
        )

        check = DisplayDoctorChecks._check_sleep_schedule()

        assert check.severity == HealthSeverity.INFO
        assert check.summary == "Sleep schedule is disabled."


class TestDoctorAPI:
    def test_doctor_endpoint_requires_auth(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _patch_settings(monkeypatch, tmp_path)
        app = create_app()
        with TestClient(app) as client:
            response = client.get("/api/admin/doctor")
            assert response.status_code == 401

    def test_doctor_endpoint_with_session(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _patch_settings(monkeypatch, tmp_path)
        app = create_app()
        with TestClient(app, raise_server_exceptions=True) as client:
            client.post(
                "/api/setup",
                json={
                    "username": "testadmin",
                    "password": "testpass123",
                    "confirm_password": "testpass123",
                },
            )

            response = client.get("/api/admin/doctor")
            assert response.status_code == 200
            body = response.json()
            assert "overall_status" in body
            assert "groups" in body
            assert "checked_at" in body

    def test_doctor_response_shape(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _patch_settings(monkeypatch, tmp_path)
        app = create_app()
        with TestClient(app, raise_server_exceptions=True) as client:
            client.post(
                "/api/setup",
                json={
                    "username": "testadmin",
                    "password": "testpass123",
                    "confirm_password": "testpass123",
                },
            )

            response = client.get("/api/admin/doctor")
            body = response.json()

            assert body["overall_status"] in ["ok", "warning", "error", "info"]
            assert isinstance(body["groups"], list)
            assert len(body["groups"]) > 0

            for group in body["groups"]:
                assert "id" in group
                assert "title" in group
                assert "status" in group
                assert "checks" in group
                assert isinstance(group["checks"], list)

                for check in group["checks"]:
                    assert "id" in check
                    assert "title" in check
                    assert "severity" in check
                    assert "summary" in check

    def test_doctor_refresh_endpoint(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _patch_settings(monkeypatch, tmp_path)
        app = create_app()
        with TestClient(app, raise_server_exceptions=True) as client:
            client.post(
                "/api/setup",
                json={
                    "username": "testadmin",
                    "password": "testpass123",
                    "confirm_password": "testpass123",
                },
            )

            response = client.post("/api/admin/doctor/refresh")
            assert response.status_code == 200
            body = response.json()
            assert "overall_status" in body

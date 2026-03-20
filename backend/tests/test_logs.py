from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.services.log_service import DEFAULT_LINE_LIMIT, LogService


def _write_log(path: Path, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = "\n".join(lines)
    if lines:
        content += "\n"
    path.write_text(content, encoding="utf-8")


@pytest.fixture()
def log_service(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> LogService:
    monkeypatch.setattr(settings, "log_dir", tmp_path / "logs")
    return LogService()


class TestLogService:
    def test_returns_empty_response_when_no_log_files_exist(
        self, log_service: LogService
    ) -> None:
        response = log_service.get_logs()

        assert response.files == []
        assert response.selected_file is None
        assert response.line_limit == DEFAULT_LINE_LIMIT
        assert response.total_lines == 0
        assert response.truncated is False
        assert response.lines == []
        assert response.fetched_at

    def test_prefers_current_log_file_when_none_selected(
        self, log_service: LogService
    ) -> None:
        _write_log(settings.log_dir / "spf5000.log.1", ["backup-1"])
        _write_log(settings.log_dir / "spf5000.log", ["current-1", "current-2"])
        _write_log(settings.log_dir / "spf5000.log.2", ["backup-2"])
        _write_log(settings.log_dir / "other.log", ["ignore me"])

        response = log_service.get_logs(line_limit=1)

        assert [file.name for file in response.files] == [
            "spf5000.log",
            "spf5000.log.1",
            "spf5000.log.2",
        ]
        assert response.selected_file == "spf5000.log"
        assert response.total_lines == 2
        assert response.truncated is True
        assert response.lines == ["current-2"]

    def test_returns_download_path_for_current_log_when_none_selected(
        self, log_service: LogService
    ) -> None:
        _write_log(settings.log_dir / "spf5000.log.1", ["backup-1"])
        _write_log(settings.log_dir / "spf5000.log", ["current-1"])

        path = log_service.get_log_download_path()

        assert path == (settings.log_dir / "spf5000.log").resolve()

    def test_returns_download_path_for_selected_rotated_log(
        self, log_service: LogService
    ) -> None:
        _write_log(settings.log_dir / "spf5000.log", ["current"])
        _write_log(settings.log_dir / "spf5000.log.2", ["backup-2"])

        path = log_service.get_log_download_path(selected_file="spf5000.log.2")

        assert path == (settings.log_dir / "spf5000.log.2").resolve()


class TestLogAPI:
    def test_logs_endpoint_requires_authentication(self, fresh_client: TestClient) -> None:
        response = fresh_client.get("/api/admin/logs")

        assert response.status_code == 401

    def test_download_logs_endpoint_requires_authentication(
        self, fresh_client: TestClient
    ) -> None:
        response = fresh_client.get("/api/admin/logs/download")

        assert response.status_code == 401

    def test_logs_endpoint_returns_empty_response_when_no_files_exist(
        self, test_client: TestClient
    ) -> None:
        response = test_client.get("/api/admin/logs")

        assert response.status_code == 200
        assert response.json() == {
            "files": [],
            "selected_file": None,
            "line_limit": DEFAULT_LINE_LIMIT,
            "total_lines": 0,
            "truncated": False,
            "lines": [],
            "fetched_at": response.json()["fetched_at"],
        }

    def test_logs_endpoint_returns_file_listing_and_trailing_lines(
        self, test_client: TestClient
    ) -> None:
        _write_log(settings.log_dir / "spf5000.log", ["line-1", "line-2", "line-3", "line-4"])
        _write_log(settings.log_dir / "spf5000.log.1", ["backup-1"])
        _write_log(settings.log_dir / "spf5000.log.2", ["backup-2"])
        _write_log(settings.log_dir / "spf5000.log.3", ["backup-3"])
        _write_log(settings.log_dir / "unmanaged.log", ["do not expose"])

        response = test_client.get("/api/admin/logs", params={"limit": 3})

        assert response.status_code == 200
        body = response.json()
        assert [file["name"] for file in body["files"]] == [
            "spf5000.log",
            "spf5000.log.1",
            "spf5000.log.2",
            "spf5000.log.3",
        ]
        assert body["selected_file"] == "spf5000.log"
        assert body["line_limit"] == 3
        assert body["total_lines"] == 4
        assert body["truncated"] is True
        assert body["lines"] == ["line-2", "line-3", "line-4"]
        assert body["files"][0]["is_current"] is True
        assert all(file["name"] != "unmanaged.log" for file in body["files"])
        assert body["fetched_at"]

    def test_logs_endpoint_reads_selected_rotated_file(
        self, test_client: TestClient
    ) -> None:
        _write_log(settings.log_dir / "spf5000.log", ["current"])
        _write_log(settings.log_dir / "spf5000.log.1", ["old-1", "old-2", "old-3"])

        response = test_client.get(
            "/api/admin/logs", params={"file": "spf5000.log.1", "limit": 2}
        )

        assert response.status_code == 200
        body = response.json()
        assert body["selected_file"] == "spf5000.log.1"
        assert body["line_limit"] == 2
        assert body["total_lines"] == 3
        assert body["truncated"] is True
        assert body["lines"] == ["old-2", "old-3"]

    def test_logs_endpoint_rejects_unmanaged_file_requests(
        self, test_client: TestClient
    ) -> None:
        response = test_client.get("/api/admin/logs", params={"file": "../secrets.txt"})

        assert response.status_code == 400
        assert response.json()["detail"] == "Requested log file is not managed by SPF5000."

    def test_logs_endpoint_returns_not_found_for_missing_managed_file(
        self, test_client: TestClient
    ) -> None:
        _write_log(settings.log_dir / "spf5000.log", ["current"])

        response = test_client.get("/api/admin/logs", params={"file": "spf5000.log.2"})

        assert response.status_code == 404
        assert response.json()["detail"] == "Requested log file does not exist."

    def test_log_download_endpoint_returns_not_found_when_no_logs_exist(
        self, test_client: TestClient
    ) -> None:
        response = test_client.get("/api/admin/logs/download")

        assert response.status_code == 404
        assert response.json()["detail"] == "No managed log files are available."

    def test_download_logs_endpoint_returns_current_file_when_unset(
        self, test_client: TestClient
    ) -> None:
        _write_log(settings.log_dir / "spf5000.log", ["current-1", "current-2"])
        _write_log(settings.log_dir / "spf5000.log.1", ["backup"])

        response = test_client.get("/api/admin/logs/download")

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/plain")
        assert response.headers["content-disposition"] == 'attachment; filename="spf5000.log"'
        assert response.text == "current-1\ncurrent-2\n"

    def test_download_logs_endpoint_returns_selected_rotated_file(
        self, test_client: TestClient
    ) -> None:
        _write_log(settings.log_dir / "spf5000.log", ["current"])
        _write_log(settings.log_dir / "spf5000.log.1", ["old-1", "old-2"])

        response = test_client.get(
            "/api/admin/logs/download", params={"file": "spf5000.log.1"}
        )

        assert response.status_code == 200
        assert (
            response.headers["content-disposition"]
            == 'attachment; filename="spf5000.log.1"'
        )
        assert response.text == "old-1\nold-2\n"

    def test_download_logs_endpoint_rejects_unmanaged_file_requests(
        self, test_client: TestClient
    ) -> None:
        response = test_client.get(
            "/api/admin/logs/download", params={"file": "../secrets.txt"}
        )

        assert response.status_code == 400
        assert (
            response.json()["detail"]
            == "Requested log file is not managed by SPF5000."
        )

    def test_download_logs_endpoint_returns_not_found_for_missing_file(
        self, test_client: TestClient
    ) -> None:
        _write_log(settings.log_dir / "spf5000.log", ["current"])

        response = test_client.get(
            "/api/admin/logs/download", params={"file": "spf5000.log.2"}
        )

        assert response.status_code == 404
        assert response.json()["detail"] == "Requested log file does not exist."

from __future__ import annotations

import os
from pathlib import Path
from typing import Generator

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import create_app

_TEST_SESSION_SECRET = "spf5000-test-session-secret-32bytes!!"
_ADMIN_USERNAME = "admin"
_ADMIN_PASSWORD = "test-password-1"


@pytest.fixture(autouse=True, scope="session")
def disable_ratelimit() -> None:
    """Disable rate limiting for all tests."""
    os.environ["SPF5000_RATE_LIMIT"] = "false"


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
    monkeypatch.setattr(settings, "session_secret", _TEST_SESSION_SECRET)


@pytest.fixture()
def fresh_client(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Generator[TestClient, None, None]:
    """A TestClient for a fresh (un-bootstrapped) install with no admin session."""
    _patch_settings(monkeypatch, tmp_path)
    app = create_app()
    with TestClient(app, raise_server_exceptions=True) as client:
        yield client


@pytest.fixture()
def test_client(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Generator[TestClient, None, None]:
    """A TestClient that has completed setup and holds a valid admin session.

    Used by existing tests that exercise admin-protected routes.
    """
    _patch_settings(monkeypatch, tmp_path)
    app = create_app()
    with TestClient(app, raise_server_exceptions=True) as client:
        resp = client.post(
            "/api/setup",
            json={
                "username": _ADMIN_USERNAME,
                "password": _ADMIN_PASSWORD,
                "confirm_password": _ADMIN_PASSWORD,
            },
        )
        assert resp.status_code == 200, f"Setup failed: {resp.text}"
        yield client

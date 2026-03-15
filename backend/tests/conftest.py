from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import create_app


@pytest.fixture()
def test_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    data_dir = tmp_path / "data"
    cache_dir = tmp_path / "cache"
    log_dir = tmp_path / "logs"

    monkeypatch.setattr(settings, "data_dir", data_dir)
    monkeypatch.setattr(settings, "cache_dir", cache_dir)
    monkeypatch.setattr(settings, "log_dir", log_dir)
    monkeypatch.setattr(settings, "database_path", data_dir / "spf5000.ddb")
    monkeypatch.setattr(settings, "frontend_dist_dir", tmp_path / "frontend-dist")
    monkeypatch.setattr(settings, "legacy_frontend_dist_dir", tmp_path / "frontend-dist-legacy")

    app = create_app()
    with TestClient(app) as client:
        yield client

from fastapi.testclient import TestClient

from app.core.version import APP_VERSION
from app.core.config import settings
from app.main import create_app


def _patch_runtime_settings(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(settings, "data_dir", tmp_path / "data")
    monkeypatch.setattr(settings, "cache_dir", tmp_path / "cache")
    monkeypatch.setattr(settings, "log_dir", tmp_path / "logs")
    monkeypatch.setattr(settings, "database_path", (tmp_path / "data") / "spf5000.ddb")
    monkeypatch.setattr(settings, "frontend_dist_dir", tmp_path / "frontend-dist")
    monkeypatch.setattr(settings, "legacy_frontend_dist_dir", tmp_path / "frontend-dist-legacy")
    monkeypatch.setattr(settings, "session_secret", "spf5000-test-session-secret-32bytes!!")


def test_health(tmp_path, monkeypatch) -> None:
    _patch_runtime_settings(tmp_path, monkeypatch)
    with TestClient(create_app()) as client:
        response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["app"] == "SPF5000"
    assert body["version"] == APP_VERSION


def test_spa_routes_fallback_to_index(tmp_path, monkeypatch) -> None:
    _patch_runtime_settings(tmp_path, monkeypatch)
    dist_dir = tmp_path / "frontend-dist"
    dist_dir.mkdir()
    (dist_dir / "index.html").write_text("<html><body>spf5000-ui</body></html>", encoding="utf-8")

    monkeypatch.setattr(settings, "frontend_dist_dir", dist_dir)
    monkeypatch.setattr(settings, "legacy_frontend_dist_dir", tmp_path / "frontend-dist-legacy")

    with TestClient(create_app()) as client:
        response = client.get("/display")

    assert response.status_code == 200
    assert "spf5000-ui" in response.text


def test_missing_static_asset_stays_404(tmp_path, monkeypatch) -> None:
    _patch_runtime_settings(tmp_path, monkeypatch)
    dist_dir = tmp_path / "frontend-dist"
    dist_dir.mkdir()
    (dist_dir / "index.html").write_text("<html><body>spf5000-ui</body></html>", encoding="utf-8")

    monkeypatch.setattr(settings, "frontend_dist_dir", dist_dir)
    monkeypatch.setattr(settings, "legacy_frontend_dist_dir", tmp_path / "frontend-dist-legacy")

    with TestClient(create_app()) as client:
        response = client.get("/assets/missing.js")

    assert response.status_code == 404

"""Tests for GET/PUT /api/settings — covering theme fields added in the
token-based theme system scaffold (ADR 0019)."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import create_app

_TEST_SESSION_SECRET = "spf5000-test-session-secret-32bytes!!"
_ADMIN_USERNAME = "admin"
_ADMIN_PASSWORD = "test-password-1"

_FULL_SETTINGS_PAYLOAD = {
    "frame_name": "Test Frame",
    "display_variant_width": 1920,
    "display_variant_height": 1080,
    "thumbnail_max_size": 400,
    "slideshow_interval_seconds": 30,
    "transition_mode": "slide",
    "transition_duration_ms": 700,
    "fit_mode": "contain",
    "shuffle_enabled": True,
    "shuffle_bag_enabled": False,
    "selected_collection_id": "default-collection",
    "active_display_profile_id": "default-display-profile",
    "background_fill_mode": "black",
    "theme_id": "default-dark",
    "home_city_accent_style": "default",
}


def _patch_settings(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    cache_dir = tmp_path / "cache"
    log_dir = tmp_path / "logs"
    monkeypatch.setattr(settings, "data_dir", data_dir)
    monkeypatch.setattr(settings, "cache_dir", cache_dir)
    monkeypatch.setattr(settings, "log_dir", log_dir)
    monkeypatch.setattr(settings, "database_path", data_dir / "spf5000.ddb")
    monkeypatch.setattr(settings, "frontend_dist_dir", tmp_path / "frontend-dist")
    monkeypatch.setattr(settings, "legacy_frontend_dist_dir", tmp_path / "frontend-dist-legacy")
    monkeypatch.setattr(settings, "session_secret", _TEST_SESSION_SECRET)


@pytest.fixture()
def test_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
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


# ── GET /api/settings — default theme fields ──────────────────────────────────


def test_get_settings_includes_theme_defaults(test_client: TestClient) -> None:
    resp = test_client.get("/api/settings")
    assert resp.status_code == 200
    body = resp.json()
    assert body["theme_id"] == "default-dark", "Default theme_id should be 'default-dark'"
    assert body["home_city_accent_style"] == "default", (
        "Default home_city_accent_style should be 'default'"
    )


# ── PUT /api/settings — theme fields round-trip ───────────────────────────────


def test_put_settings_persists_theme_id(test_client: TestClient) -> None:
    payload = {**_FULL_SETTINGS_PAYLOAD, "theme_id": "retro-neon"}
    resp = test_client.put("/api/settings", json=payload)
    assert resp.status_code == 200
    assert resp.json()["theme_id"] == "retro-neon"

    # Confirm persistence: re-fetch and check
    get_resp = test_client.get("/api/settings")
    assert get_resp.status_code == 200
    assert get_resp.json()["theme_id"] == "retro-neon"


def test_put_settings_persists_home_city_accent_style(test_client: TestClient) -> None:
    payload = {**_FULL_SETTINGS_PAYLOAD, "home_city_accent_style": "glow"}
    resp = test_client.put("/api/settings", json=payload)
    assert resp.status_code == 200
    assert resp.json()["home_city_accent_style"] == "glow"

    get_resp = test_client.get("/api/settings")
    assert get_resp.status_code == 200
    assert get_resp.json()["home_city_accent_style"] == "glow"


def test_put_settings_omitting_theme_fields_uses_defaults(test_client: TestClient) -> None:
    """A PUT that omits theme_id and home_city_accent_style should apply defaults."""
    payload = {k: v for k, v in _FULL_SETTINGS_PAYLOAD.items()
               if k not in ("theme_id", "home_city_accent_style")}
    resp = test_client.put("/api/settings", json=payload)
    assert resp.status_code == 200
    body = resp.json()
    assert body["theme_id"] == "default-dark"
    assert body["home_city_accent_style"] == "default"


def test_put_settings_round_trips_all_theme_fields(test_client: TestClient) -> None:
    payload = {
        **_FULL_SETTINGS_PAYLOAD,
        "theme_id": "warm-family",
        "home_city_accent_style": "warm",
    }
    resp = test_client.put("/api/settings", json=payload)
    assert resp.status_code == 200
    body = resp.json()
    assert body["theme_id"] == "warm-family"
    assert body["home_city_accent_style"] == "warm"


# ── Auth protection — existing routes should still be guarded ─────────────────


def test_settings_requires_auth(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """GET /api/settings must return 401 without a valid admin session."""
    _patch_settings(monkeypatch, tmp_path)
    app = create_app()
    with TestClient(app, raise_server_exceptions=True) as client:
        # Bootstrap first so the app is in ready state
        client.post(
            "/api/setup",
            json={
                "username": _ADMIN_USERNAME,
                "password": _ADMIN_PASSWORD,
                "confirm_password": _ADMIN_PASSWORD,
            },
        )
        # New client with no session
        with TestClient(app, raise_server_exceptions=True) as unauthed:
            resp = unauthed.get("/api/settings")
            assert resp.status_code == 401


def test_put_settings_requires_auth(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """PUT /api/settings must return 401 without a valid admin session."""
    _patch_settings(monkeypatch, tmp_path)
    app = create_app()
    with TestClient(app, raise_server_exceptions=True) as client:
        client.post(
            "/api/setup",
            json={
                "username": _ADMIN_USERNAME,
                "password": _ADMIN_PASSWORD,
                "confirm_password": _ADMIN_PASSWORD,
            },
        )
        with TestClient(app, raise_server_exceptions=True) as unauthed:
            resp = unauthed.put("/api/settings", json=_FULL_SETTINGS_PAYLOAD)
            assert resp.status_code == 401

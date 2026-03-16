"""Tests for GET /api/themes — public themes endpoint (ADR 0019 scaffold)."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import create_app

_TEST_SESSION_SECRET = "spf5000-test-session-secret-32bytes!!"
_ADMIN_USERNAME = "admin"
_ADMIN_PASSWORD = "test-password-1"


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
def fresh_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """A client with no admin session — used to verify public access."""
    _patch_settings(monkeypatch, tmp_path)
    app = create_app()
    with TestClient(app, raise_server_exceptions=True) as client:
        yield client


@pytest.fixture()
def test_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """A client with a valid admin session."""
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


# ── Public access ─────────────────────────────────────────────────────────────


def test_get_themes_is_public(fresh_client: TestClient) -> None:
    """GET /api/themes must succeed with no auth (display client uses it)."""
    resp = fresh_client.get("/api/themes")
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"


# ── Response shape ────────────────────────────────────────────────────────────


def test_get_themes_response_shape(fresh_client: TestClient) -> None:
    resp = fresh_client.get("/api/themes")
    assert resp.status_code == 200
    body = resp.json()

    assert "active_theme_id" in body
    assert "home_city_accent_style" in body
    assert "themes" in body
    assert isinstance(body["themes"], list)


def test_get_themes_default_active_selection(fresh_client: TestClient) -> None:
    """Before any settings are changed, active_theme_id should be 'default-dark'."""
    resp = fresh_client.get("/api/themes")
    assert resp.status_code == 200
    body = resp.json()
    assert body["active_theme_id"] == "default-dark"
    assert body["home_city_accent_style"] == "default"


def test_get_themes_returns_builtin_themes(fresh_client: TestClient) -> None:
    """All four built-in themes must be present in the response."""
    resp = fresh_client.get("/api/themes")
    assert resp.status_code == 200
    theme_ids = {t["id"] for t in resp.json()["themes"]}
    expected = {"default-dark", "retro-neon", "purple-dream", "warm-family"}
    assert expected <= theme_ids, f"Missing built-in themes: {expected - theme_ids}"


def test_get_themes_each_has_required_fields(fresh_client: TestClient) -> None:
    resp = fresh_client.get("/api/themes")
    assert resp.status_code == 200
    for theme in resp.json()["themes"]:
        assert "id" in theme
        assert "name" in theme
        assert "description" in theme
        assert "version" in theme
        assert "tokens" in theme
        tokens = theme["tokens"]
        assert "colors" in tokens
        assert "typography" in tokens


def test_get_themes_token_values_are_strings(fresh_client: TestClient) -> None:
    resp = fresh_client.get("/api/themes")
    assert resp.status_code == 200
    for theme in resp.json()["themes"]:
        for cat_name, cat in theme["tokens"].items():
            for key, val in cat.items():
                assert isinstance(val, str), (
                    f"Token {theme['id']}.tokens.{cat_name}.{key!r} should be a string, got {type(val)}"
                )


def test_get_themes_has_components_and_contexts(fresh_client: TestClient) -> None:
    resp = fresh_client.get("/api/themes")
    assert resp.status_code == 200
    for theme in resp.json()["themes"]:
        assert "components" in theme
        assert "contexts" in theme
        assert isinstance(theme["components"], dict)
        assert isinstance(theme["contexts"], dict)


# ── Active selection follows settings ─────────────────────────────────────────


def test_get_themes_reflects_updated_theme_id(test_client: TestClient) -> None:
    """After updating theme_id in settings, GET /api/themes should reflect it."""
    # Change the active theme via settings
    put_resp = test_client.put(
        "/api/settings",
        json={
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
            "theme_id": "retro-neon",
            "home_city_accent_style": "glow",
        },
    )
    assert put_resp.status_code == 200

    themes_resp = test_client.get("/api/themes")
    assert themes_resp.status_code == 200
    body = themes_resp.json()
    assert body["active_theme_id"] == "retro-neon"
    assert body["home_city_accent_style"] == "glow"


# ── Theme service unit-level: validation of a bad theme file ──────────────────


def test_theme_service_skips_invalid_theme_file(tmp_path: Path) -> None:
    """ThemeService must skip theme files that fail schema validation."""
    import json

    from app.services.theme_service import ThemeService

    themes_dir = tmp_path / "themes"
    themes_dir.mkdir()

    # Write a valid theme
    valid = {
        "id": "my-theme",
        "name": "My Theme",
        "description": "A test theme",
        "version": "1.0.0",
        "tokens": {
            "colors": {
                "background_primary": "#000",
                "text_primary": "#fff",
                "accent_primary": "#0af",
                "display_background": "#000",
            },
            "typography": {
                "font_family_base": "sans-serif",
                "font_size_md": "1rem",
                "font_weight_normal": "400",
            },
        },
    }
    (themes_dir / "my-theme.json").write_text(json.dumps(valid), encoding="utf-8")

    # Write an invalid theme (missing required token keys)
    invalid = {
        "id": "bad-theme",
        "name": "Bad",
        "description": "Missing required tokens",
        "version": "1.0.0",
        "tokens": {
            "colors": {},
            "typography": {},
        },
    }
    (themes_dir / "bad-theme.json").write_text(json.dumps(invalid), encoding="utf-8")

    service = ThemeService(themes_dir=themes_dir)
    # Force load via private method (tests internals deliberately)
    loaded = service._get_themes()

    ids = [t.id for t in loaded]
    assert "my-theme" in ids
    assert "bad-theme" not in ids


def test_theme_service_rejects_id_mismatch(tmp_path: Path) -> None:
    """ThemeService must skip a file whose internal id doesn't match the filename."""
    import json

    from app.services.theme_service import ThemeService

    themes_dir = tmp_path / "themes"
    themes_dir.mkdir()

    theme = {
        "id": "wrong-id",
        "name": "Mismatch",
        "description": "id in file does not match filename",
        "version": "1.0.0",
        "tokens": {
            "colors": {
                "background_primary": "#000",
                "text_primary": "#fff",
                "accent_primary": "#0af",
                "display_background": "#000",
            },
            "typography": {
                "font_family_base": "sans-serif",
                "font_size_md": "1rem",
                "font_weight_normal": "400",
            },
        },
    }
    # File is named correctly-named.json but id inside is wrong-id
    (themes_dir / "correctly-named.json").write_text(json.dumps(theme), encoding="utf-8")

    service = ThemeService(themes_dir=themes_dir)
    loaded = service._get_themes()
    assert not loaded

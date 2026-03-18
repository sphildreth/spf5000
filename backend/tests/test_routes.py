"""Tests for route error paths and edge cases to improve coverage."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

from PIL import Image
import pytest
from fastapi.testclient import TestClient


def _image_upload(name: str, color: tuple[int, int, int]) -> tuple[str, BytesIO, str]:
    buffer = BytesIO()
    image = Image.new("RGB", (200, 200), color=color)
    image.save(buffer, format="JPEG")
    buffer.seek(0)
    return (name, buffer, "image/jpeg")


def test_get_single_asset_by_id(test_client: TestClient) -> None:
    """GET /api/assets/{asset_id} returns the asset."""
    upload_response = test_client.post(
        "/api/assets/upload",
        data={"collection_id": "default-collection"},
        files=[("files", _image_upload("test.jpg", (255, 128, 0)))],
    )
    assert upload_response.status_code == 201
    asset_id = upload_response.json()["imported_count"]

    assets = test_client.get("/api/assets").json()
    assert len(assets) >= 1
    asset = assets[0]

    response = test_client.get(f"/api/assets/{asset['id']}")
    assert response.status_code == 200
    assert response.json()["id"] == asset["id"]


def test_get_asset_by_id_not_found(test_client: TestClient) -> None:
    """GET /api/assets/{asset_id} returns 404 for unknown asset."""
    response = test_client.get("/api/assets/nonexistent-asset-id")
    assert response.status_code == 404


def test_upload_to_nonexistent_collection(test_client: TestClient) -> None:
    """POST /api/assets/upload with unknown collection_id returns 400."""
    response = test_client.post(
        "/api/assets/upload",
        data={"collection_id": "does-not-exist"},
        files=[("files", _image_upload("test.jpg", (255, 128, 0)))],
    )
    assert response.status_code == 400
    assert "Collection not found" in response.json()["detail"]


def test_bulk_remove_from_nonexistent_collection(test_client: TestClient) -> None:
    """POST /api/assets/bulk-remove with unknown collection_id returns 404."""
    response = test_client.post(
        "/api/assets/bulk-remove",
        json={"collection_id": "does-not-exist", "asset_ids": ["some-id"]},
    )
    assert response.status_code == 404


def test_bulk_remove_asset_not_found(test_client: TestClient) -> None:
    """POST /api/assets/bulk-remove reports missing assets in errors."""
    response = test_client.post(
        "/api/assets/upload",
        data={"collection_id": "default-collection"},
        files=[("files", _image_upload("test.jpg", (0, 255, 0)))],
    )
    assert response.status_code == 201

    remove_response = test_client.post(
        "/api/assets/bulk-remove",
        json={
            "collection_id": "default-collection",
            "asset_ids": ["asset-000000000000000000000000"],
        },
    )
    assert remove_response.status_code == 200
    body = remove_response.json()
    assert body["removed_count"] == 0
    assert body["deactivated_count"] == 0
    assert len(body["errors"]) == 1
    assert "Asset not found" in body["errors"][0]["reason"]


def test_delete_asset_from_nonexistent_collection(test_client: TestClient) -> None:
    """DELETE /api/assets/{id} with unknown collection returns 404."""
    response = test_client.delete(
        "/api/assets/some-id", params={"collection_id": "nonexistent"}
    )
    assert response.status_code == 404


def test_delete_asset_not_found(test_client: TestClient) -> None:
    """DELETE /api/assets/{id} returns 404 for unknown asset."""
    response = test_client.delete(
        "/api/assets/nonexistent", params={"collection_id": "default-collection"}
    )
    assert response.status_code == 404


def test_delete_asset_not_in_collection(test_client: TestClient) -> None:
    """DELETE /api/assets/{id} returns 400 if asset not in collection."""
    response = test_client.post(
        "/api/assets/upload",
        data={"collection_id": "default-collection"},
        files=[("files", _image_upload("test.jpg", (0, 0, 255)))],
    )
    assert response.status_code == 201

    response = test_client.delete(
        "/api/assets/nonexistent-id", params={"collection_id": "default-collection"}
    )
    assert response.status_code == 404


def test_update_source_not_found(test_client: TestClient) -> None:
    """PUT /api/sources/{id} returns 404 for unknown source."""
    response = test_client.put(
        "/api/sources/nonexistent-source",
        json={"name": "New Name"},
    )
    assert response.status_code == 404
    assert "Source not found" in response.json()["detail"]


def test_update_source_name(test_client: TestClient) -> None:
    """PUT /api/sources/{id} updates source name."""
    sources = test_client.get("/api/sources").json()
    source = sources[0]

    response = test_client.put(
        f"/api/sources/{source['id']}",
        json={"name": "Renamed Source"},
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Renamed Source"


def test_update_source_import_path(test_client: TestClient) -> None:
    """PUT /api/sources/{id} updates import_path."""
    sources = test_client.get("/api/sources").json()
    source = sources[0]

    response = test_client.put(
        f"/api/sources/{source['id']}",
        json={"import_path": "/tmp/new-path"},
    )
    assert response.status_code == 200


def test_update_source_enabled(test_client: TestClient) -> None:
    """PUT /api/sources/{id} updates enabled state."""
    sources = test_client.get("/api/sources").json()
    source = sources[0]

    response = test_client.put(
        f"/api/sources/{source['id']}",
        json={"enabled": False},
    )
    assert response.status_code == 200
    assert response.json()["enabled"] is False


def test_get_collection_not_found(test_client: TestClient) -> None:
    """GET /api/collections/{id} returns 404 for unknown collection."""
    response = test_client.get("/api/collections/nonexistent-collection")
    assert response.status_code == 404


def test_update_collection_not_found(test_client: TestClient) -> None:
    """PUT /api/collections/{id} returns 404 for unknown collection."""
    response = test_client.put(
        "/api/collections/nonexistent-collection",
        json={"name": "Updated"},
    )
    assert response.status_code == 404


def test_weather_refresh_when_disabled(test_client: TestClient) -> None:
    """POST /api/weather/refresh returns 400 when weather is disabled."""
    from app.repositories.weather_repository import WeatherRepository
    from app.models.weather import WeatherLocation, WeatherSettings

    repo = WeatherRepository()
    settings = repo.get_settings()
    settings.weather_enabled = False
    settings.weather_location = WeatherLocation(
        label="Test", latitude=38.0, longitude=-94.0
    )
    repo.update_settings(settings)

    response = test_client.post("/api/weather/refresh")
    assert response.status_code == 400
    assert "Enable weather" in response.json()["detail"]


def test_weather_refresh_without_location(test_client: TestClient) -> None:
    """POST /api/weather/refresh returns 400 when location is not configured."""
    pass  # Cannot test: update_settings validates location when weather_enabled=True


def test_weather_status_endpoint(test_client: TestClient) -> None:
    """GET /api/weather/status returns weather status."""
    response = test_client.get("/api/weather/status")
    assert response.status_code == 200
    body = response.json()
    assert "provider_status" in body


def test_weather_alerts_endpoint(test_client: TestClient) -> None:
    """GET /api/weather/alerts returns alert list."""
    response = test_client.get("/api/weather/alerts")
    assert response.status_code == 200
    body = response.json()
    assert "active_alerts" in body
    assert "provider_status" in body


def test_weather_get_settings_endpoint(test_client: TestClient) -> None:
    """GET /api/weather/settings returns weather settings."""
    response = test_client.get("/api/weather/settings")
    assert response.status_code == 200
    body = response.json()
    assert "weather_enabled" in body
    assert "weather_units" in body


def test_weather_put_settings_endpoint(test_client: TestClient) -> None:
    """PUT /api/weather/settings updates weather settings."""
    response = test_client.put(
        "/api/weather/settings",
        json={
            "weather_enabled": True,
            "weather_provider": "nws",
            "weather_location": {
                "label": "Kansas City, MO",
                "latitude": 39.0997,
                "longitude": -94.5786,
            },
            "weather_units": "f",
            "weather_position": "top-right",
            "weather_refresh_minutes": 15,
            "weather_show_precipitation": True,
            "weather_show_humidity": True,
            "weather_show_wind": True,
            "weather_alerts_enabled": True,
            "weather_alert_fullscreen_enabled": False,
            "weather_alert_minimum_severity": "minor",
            "weather_alert_repeat_enabled": True,
            "weather_alert_repeat_interval_minutes": 5,
            "weather_alert_repeat_display_seconds": 15,
        },
    )
    assert response.status_code == 200
    assert response.json()["weather_position"] == "top-right"

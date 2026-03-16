from __future__ import annotations

from pathlib import Path

from PIL import Image


def _write_sample_image(path: Path, color: tuple[int, int, int]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    image = Image.new("RGB", (1200, 800), color=color)
    image.save(path, format="JPEG")


def test_status_bootstrap_and_settings_update(test_client) -> None:
    status_response = test_client.get("/api/status")
    assert status_response.status_code == 200
    status_body = status_response.json()
    assert status_body["status"] == "ready"
    assert status_body["source_count"] >= 1
    assert status_body["collection_count"] >= 1
    assert "warnings" in status_body
    assert status_body["active_display_profile"]["selected_collection_id"] == "default-collection"

    settings_response = test_client.get("/api/settings")
    assert settings_response.status_code == 200
    assert settings_response.json()["frame_name"] == "SPF5000"
    assert settings_response.json()["display_variant_width"] == 1920
    assert settings_response.json()["slideshow_interval_seconds"] == 30

    update_response = test_client.put(
        "/api/settings",
        json={
            "frame_name": "Kitchen Frame",
            "display_variant_width": 1600,
            "display_variant_height": 900,
            "thumbnail_max_size": 256,
            "slideshow_interval_seconds": 45,
            "transition_mode": "slide",
            "transition_duration_ms": 900,
            "fit_mode": "cover",
            "shuffle_enabled": False,
            "selected_collection_id": "default-collection",
            "active_display_profile_id": "default-display-profile",
        },
    )
    assert update_response.status_code == 200
    assert update_response.json()["frame_name"] == "Kitchen Frame"
    assert update_response.json()["display_variant_width"] == 1600
    assert update_response.json()["fit_mode"] == "cover"
    assert update_response.json()["shuffle_enabled"] is False

    display_response = test_client.get("/api/display/config")
    assert display_response.status_code == 200
    assert display_response.json()["idle_message"]
    assert display_response.json()["refresh_interval_seconds"] == 60


def test_collections_crud(test_client) -> None:
    create_response = test_client.post(
        "/api/collections",
        json={
            "name": "Favorites",
            "description": "Hand-picked photos",
            "source_id": "default-local-files",
            "is_active": True,
        },
    )
    assert create_response.status_code == 201
    created = create_response.json()
    assert created["name"] == "Favorites"

    update_response = test_client.put(
        f"/api/collections/{created['id']}",
        json={"description": "Updated", "is_active": False},
    )
    assert update_response.status_code == 200
    updated = update_response.json()
    assert updated["description"] == "Updated"
    assert updated["is_active"] is False

    list_response = test_client.get("/api/collections")
    assert list_response.status_code == 200
    assert any(item["id"] == created["id"] for item in list_response.json())


def test_local_scan_import_assets_and_playlist(test_client) -> None:
    sources_response = test_client.get("/api/sources")
    assert sources_response.status_code == 200
    source = next(item for item in sources_response.json() if item["provider_type"] == "local_files")
    import_dir = Path(source["import_path"])

    _write_sample_image(import_dir / "one.jpg", (255, 0, 0))
    _write_sample_image(import_dir / "nested" / "two.jpg", (0, 255, 0))
    (import_dir / "ignore.txt").write_text("not an image", encoding="utf-8")

    scan_response = test_client.post("/api/import/local/scan", json={"source_id": source["id"], "max_samples": 5})
    assert scan_response.status_code == 200
    scan_body = scan_response.json()
    assert scan_body["discovered_count"] == 2
    assert scan_body["ignored_count"] == 1

    run_response = test_client.post(
        "/api/import/local/run",
        json={
            "source_id": source["id"],
            "collection_id": "default-collection",
            "max_samples": 5,
        },
    )
    assert run_response.status_code == 200
    run_body = run_response.json()
    assert run_body["imported_count"] == 2
    assert run_body["duplicate_count"] == 0

    assets_response = test_client.get("/api/assets")
    assert assets_response.status_code == 200
    assets = assets_response.json()
    assert len(assets) == 2
    first_asset = assets[0]
    assert first_asset["thumbnail_url"]
    assert first_asset["display_url"]

    variant_response = test_client.get(first_asset["display_url"])
    assert variant_response.status_code == 200
    assert variant_response.headers["content-type"].startswith("image/jpeg")

    playlist_response = test_client.get("/api/display/playlist")
    assert playlist_response.status_code == 200
    playlist = playlist_response.json()
    assert playlist["collection_id"] == "default-collection"
    assert len(playlist["items"]) == 2

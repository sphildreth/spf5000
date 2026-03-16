from __future__ import annotations

from io import BytesIO
from pathlib import Path

from PIL import Image


def _write_sample_image(path: Path, color: tuple[int, int, int]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    image = Image.new("RGB", (1200, 800), color=color)
    image.save(path, format="JPEG")


def _image_upload(name: str, color: tuple[int, int, int]) -> tuple[str, BytesIO, str]:
    buffer = BytesIO()
    image = Image.new("RGB", (1200, 800), color=color)
    image.save(buffer, format="JPEG")
    buffer.seek(0)
    return (name, buffer, "image/jpeg")


def _image_upload_with_size(name: str, color: tuple[int, int, int], size: tuple[int, int]) -> tuple[str, BytesIO, str]:
    buffer = BytesIO()
    image = Image.new("RGB", size, color=color)
    image.save(buffer, format="JPEG")
    buffer.seek(0)
    return (name, buffer, "image/jpeg")


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


def test_batch_upload_imports_assets_into_selected_collection(test_client) -> None:
    collection_response = test_client.post(
        "/api/collections",
        json={
            "name": "Uploaded photos",
            "description": "Browser-uploaded assets",
            "source_id": "default-local-files",
            "is_active": True,
        },
    )
    assert collection_response.status_code == 201
    collection_id = collection_response.json()["id"]

    upload_response = test_client.post(
        "/api/assets/upload",
        data={"collection_id": collection_id},
        files=[
            ("files", _image_upload("one.jpg", (255, 0, 0))),
            ("files", _image_upload("two.jpg", (0, 255, 0))),
        ],
    )
    assert upload_response.status_code == 201
    body = upload_response.json()
    assert body["collection_id"] == collection_id
    assert body["imported_count"] == 2
    assert body["duplicate_count"] == 0
    assert body["error_count"] == 0

    collection_assets_response = test_client.get("/api/assets", params={"collection_id": collection_id})
    assert collection_assets_response.status_code == 200
    assets = collection_assets_response.json()
    assert len(assets) == 2
    assert {asset["source_id"] for asset in assets} == {"default-local-files"}

    collections_response = test_client.get("/api/collections")
    assert collections_response.status_code == 200
    created_collection = next(item for item in collections_response.json() if item["id"] == collection_id)
    assert created_collection["asset_count"] == 2


def test_remove_asset_from_collection_deactivates_unassigned_asset(test_client) -> None:
    upload_response = test_client.post(
        "/api/assets/upload",
        data={"collection_id": "default-collection"},
        files=[
            ("files", _image_upload("remove-me.jpg", (255, 0, 0))),
        ],
    )
    assert upload_response.status_code == 201

    assets_response = test_client.get("/api/assets", params={"collection_id": "default-collection"})
    assert assets_response.status_code == 200
    assets = assets_response.json()
    assert len(assets) == 1
    asset_id = assets[0]["id"]

    delete_response = test_client.delete(f"/api/assets/{asset_id}", params={"collection_id": "default-collection"})
    assert delete_response.status_code == 204

    collection_assets_response = test_client.get("/api/assets", params={"collection_id": "default-collection"})
    assert collection_assets_response.status_code == 200
    assert collection_assets_response.json() == []

    all_assets_response = test_client.get("/api/assets")
    assert all_assets_response.status_code == 200
    assert all_assets_response.json() == []

    collections_response = test_client.get("/api/collections")
    assert collections_response.status_code == 200
    default_collection = next(item for item in collections_response.json() if item["id"] == "default-collection")
    assert default_collection["asset_count"] == 0


def test_display_variants_are_sized_for_cover_playback(test_client) -> None:
    settings_response = test_client.put(
        "/api/settings",
        json={
            "frame_name": "SPF5000",
            "display_variant_width": 1600,
            "display_variant_height": 900,
            "thumbnail_max_size": 400,
            "slideshow_interval_seconds": 30,
            "transition_mode": "slide",
            "transition_duration_ms": 700,
            "fit_mode": "cover",
            "shuffle_enabled": True,
            "selected_collection_id": "default-collection",
            "active_display_profile_id": "default-display-profile",
        },
    )
    assert settings_response.status_code == 200

    upload_response = test_client.post(
        "/api/assets/upload",
        data={"collection_id": "default-collection"},
        files=[
            ("files", _image_upload_with_size("wide.jpg", (255, 0, 0), (2048, 1337))),
        ],
    )
    assert upload_response.status_code == 201

    assets_response = test_client.get("/api/assets", params={"collection_id": "default-collection"})
    assert assets_response.status_code == 200
    asset = assets_response.json()[0]

    variant_response = test_client.get(asset["display_url"])
    assert variant_response.status_code == 200

    with Image.open(BytesIO(variant_response.content)) as variant_image:
        assert variant_image.width >= 1600
        assert variant_image.height >= 900
        assert variant_image.size == (1600, 1045)


def test_batch_upload_reports_duplicates_and_invalid_files(test_client) -> None:
    upload_response = test_client.post(
        "/api/assets/upload",
        data={"collection_id": "default-collection"},
        files=[
            ("files", _image_upload("original.jpg", (12, 34, 56))),
            ("files", _image_upload("duplicate.jpg", (12, 34, 56))),
            ("files", ("notes.txt", BytesIO(b"not an image"), "text/plain")),
        ],
    )
    assert upload_response.status_code == 201
    body = upload_response.json()
    assert body["received_count"] == 3
    assert body["imported_count"] == 1
    assert body["duplicate_count"] == 1
    assert body["error_count"] == 1
    assert any("unsupported file type" in message for message in body["errors"])

    assets_response = test_client.get("/api/assets", params={"collection_id": "default-collection"})
    assert assets_response.status_code == 200
    assets = assets_response.json()
    assert len(assets) == 1


def test_bulk_remove_from_non_default_collection(test_client) -> None:
    # Create a non-default collection
    coll_resp = test_client.post(
        "/api/collections",
        json={"name": "Bulk Test", "description": "", "source_id": "default-local-files", "is_active": True},
    )
    assert coll_resp.status_code == 201
    collection_id = coll_resp.json()["id"]

    # Upload 2 unique assets into it
    upload_resp = test_client.post(
        "/api/assets/upload",
        data={"collection_id": collection_id},
        files=[
            ("files", _image_upload("bulk-a.jpg", (10, 20, 30))),
            ("files", _image_upload("bulk-b.jpg", (40, 50, 60))),
        ],
    )
    assert upload_resp.status_code == 201
    assert upload_resp.json()["imported_count"] == 2

    assets_resp = test_client.get("/api/assets", params={"collection_id": collection_id})
    assert assets_resp.status_code == 200
    asset_ids = [a["id"] for a in assets_resp.json()]
    assert len(asset_ids) == 2

    # Bulk-remove both
    remove_resp = test_client.post(
        "/api/assets/bulk-remove",
        json={"collection_id": collection_id, "asset_ids": asset_ids},
    )
    assert remove_resp.status_code == 200
    body = remove_resp.json()
    assert body["removed_count"] == 2
    assert body["deactivated_count"] == 2
    assert body["errors"] == []

    # Collection is now empty
    after_resp = test_client.get("/api/assets", params={"collection_id": collection_id})
    assert after_resp.status_code == 200
    assert after_resp.json() == []

    # Both assets are deactivated — absent from the global active list
    all_resp = test_client.get("/api/assets")
    assert all_resp.status_code == 200
    active_ids = {a["id"] for a in all_resp.json()}
    assert not active_ids.intersection(set(asset_ids))


def test_bulk_remove_mixed_membership(test_client) -> None:
    # Create two collections
    coll1_resp = test_client.post(
        "/api/collections",
        json={"name": "Alpha", "description": "", "source_id": "default-local-files", "is_active": True},
    )
    assert coll1_resp.status_code == 201
    coll1_id = coll1_resp.json()["id"]

    coll2_resp = test_client.post(
        "/api/collections",
        json={"name": "Beta", "description": "", "source_id": "default-local-files", "is_active": True},
    )
    assert coll2_resp.status_code == 201
    coll2_id = coll2_resp.json()["id"]

    # Upload asset_a (red) to coll1 — unique
    test_client.post(
        "/api/assets/upload",
        data={"collection_id": coll1_id},
        files=[("files", _image_upload("asset-a.jpg", (10, 20, 30)))],
    )
    # Upload asset_b (green) to coll1 — unique
    test_client.post(
        "/api/assets/upload",
        data={"collection_id": coll1_id},
        files=[("files", _image_upload("asset-b.jpg", (70, 80, 90)))],
    )
    # Upload asset_a (same bytes) to coll2 — duplicate; ingest adds membership to coll2
    dup_resp = test_client.post(
        "/api/assets/upload",
        data={"collection_id": coll2_id},
        files=[("files", _image_upload("asset-a.jpg", (10, 20, 30)))],
    )
    assert dup_resp.status_code == 201
    assert dup_resp.json()["duplicate_count"] == 1  # membership was silently added

    # Fetch coll1 assets and identify which is asset_a (in both colls) vs asset_b (coll1 only)
    assets_resp = test_client.get("/api/assets", params={"collection_id": coll1_id})
    assert assets_resp.status_code == 200
    assets = assets_resp.json()
    assert len(assets) == 2

    asset_a_id = next(a["id"] for a in assets if coll2_id in a["collection_ids"])
    asset_b_id = next(a["id"] for a in assets if coll2_id not in a["collection_ids"])

    # Bulk-remove both from coll1
    remove_resp = test_client.post(
        "/api/assets/bulk-remove",
        json={"collection_id": coll1_id, "asset_ids": [asset_a_id, asset_b_id]},
    )
    assert remove_resp.status_code == 200
    body = remove_resp.json()
    assert body["removed_count"] == 2
    assert body["deactivated_count"] == 1  # only asset_b has no remaining membership
    assert body["errors"] == []

    # asset_a still active in coll2
    coll2_resp2 = test_client.get("/api/assets", params={"collection_id": coll2_id})
    assert coll2_resp2.status_code == 200
    coll2_assets = coll2_resp2.json()
    assert len(coll2_assets) == 1
    assert coll2_assets[0]["id"] == asset_a_id

    # asset_b is deactivated — absent from global active list
    all_resp = test_client.get("/api/assets")
    assert all_resp.status_code == 200
    active_ids = {a["id"] for a in all_resp.json()}
    assert asset_a_id in active_ids
    assert asset_b_id not in active_ids


def test_bulk_remove_rejects_empty_asset_ids(test_client) -> None:
    remove_resp = test_client.post(
        "/api/assets/bulk-remove",
        json={"collection_id": "default-collection", "asset_ids": []},
    )
    assert remove_resp.status_code == 422

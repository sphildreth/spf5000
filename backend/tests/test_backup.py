from __future__ import annotations

import io
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from PIL import Image
from fastapi.testclient import TestClient

from app.core.config import settings
from app.repositories.asset_repository import AssetRepository

_ADMIN_PASSWORD = "test-password-1"
_ADMIN_USERNAME = "admin"


def _image_upload(name: str, color: tuple[int, int, int]) -> tuple[str, io.BytesIO, str]:
    buffer = io.BytesIO()
    image = Image.new("RGB", (1200, 800), color=color)
    image.save(buffer, format="JPEG")
    buffer.seek(0)
    return (name, buffer, "image/jpeg")


def _read_zip_entries(payload: bytes) -> tuple[list[str], dict[str, object]]:
    with ZipFile(io.BytesIO(payload)) as archive:
        names = sorted(archive.namelist())
        if "backup-manifest.json" in names:
            manifest_name = "backup-manifest.json"
        else:
            manifest_name = "collection-export-manifest.json"
        manifest = json.loads(archive.read(manifest_name).decode("utf-8"))
    return names, manifest


def _make_backup_zip(*, database_name: str = "spf5000.ddb", manifest_name: str = "backup-manifest.json") -> bytes:
    buffer = io.BytesIO()
    with ZipFile(buffer, mode="w", compression=ZIP_DEFLATED) as archive:
        archive.writestr(database_name, settings.database_path.read_bytes())
        archive.writestr(
            manifest_name,
            json.dumps(
                {
                    "type": "database-backup",
                    "database_filename": "spf5000.ddb",
                    "media_included": False,
                }
            ),
        )
    return buffer.getvalue()


def test_backup_routes_require_admin_authentication(fresh_client: TestClient) -> None:
    export_response = fresh_client.get("/api/backup/database/export")
    assert export_response.status_code == 401

    import_response = fresh_client.post(
        "/api/backup/database/import",
        files={"archive": ("backup.zip", io.BytesIO(b"not-a-zip"), "application/zip")},
    )
    assert import_response.status_code == 401

    collection_response = fresh_client.get("/api/backup/collections/default-collection/export")
    assert collection_response.status_code == 401


def test_database_export_creates_zip_with_manifest(test_client: TestClient) -> None:
    response = test_client.get("/api/backup/database/export")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"
    assert "spf5000-database-backup-" in response.headers["content-disposition"]

    names, manifest = _read_zip_entries(response.content)
    assert names == ["backup-manifest.json", "spf5000.ddb"]
    assert manifest["type"] == "database-backup"
    assert manifest["database_filename"] == "spf5000.ddb"
    assert manifest["media_included"] is False

    with ZipFile(io.BytesIO(response.content)) as archive:
        assert archive.read("spf5000.ddb") == settings.database_path.read_bytes()


def test_database_import_rejects_invalid_archives(test_client: TestClient) -> None:
    cases = [
        (
            b"definitely-not-a-zip",
            "Uploaded file is not a valid ZIP archive.",
        ),
        (
            _make_backup_zip(database_name="../spf5000.ddb"),
            "Backup archive contains an invalid member path.",
        ),
        (
            _make_backup_zip(database_name="not-the-database.ddb"),
            "Backup archive must include spf5000.ddb.",
        ),
    ]

    for payload, expected_detail in cases:
        response = test_client.post(
            "/api/backup/database/import",
            files={"archive": ("backup.zip", io.BytesIO(payload), "application/zip")},
        )
        assert response.status_code == 400
        assert response.json()["detail"] == expected_detail


def test_database_import_restores_database_and_clears_session(test_client: TestClient) -> None:
    export_response = test_client.get("/api/backup/database/export")
    assert export_response.status_code == 200
    backup_bytes = export_response.content

    create_response = test_client.post(
        "/api/collections",
        json={
            "name": "Temporary restore check",
            "description": "Should disappear after restore",
            "source_id": "default-local-files",
            "is_active": True,
        },
    )
    assert create_response.status_code == 201
    created_collection_id = create_response.json()["id"]

    restore_response = test_client.post(
        "/api/backup/database/import",
        files={"archive": ("backup.zip", io.BytesIO(backup_bytes), "application/zip")},
    )
    assert restore_response.status_code == 200
    assert restore_response.json() == {
        "restored": True,
        "reauthenticate_required": True,
        "media_restored": False,
        "message": "Database restored successfully. Media files were not restored. Please sign in again.",
    }

    session_response = test_client.get("/api/auth/session")
    assert session_response.status_code == 200
    assert session_response.json() == {
        "auth_available": True,
        "bootstrapped": True,
        "authenticated": False,
        "user": None,
    }
    assert test_client.get("/api/collections").status_code == 401

    login_response = test_client.post(
        "/api/auth/login",
        json={"username": _ADMIN_USERNAME, "password": _ADMIN_PASSWORD},
    )
    assert login_response.status_code == 200

    collections_response = test_client.get("/api/collections")
    assert collections_response.status_code == 200
    assert all(item["id"] != created_collection_id for item in collections_response.json())


def test_collection_export_skips_missing_files_and_records_manifest(test_client: TestClient) -> None:
    collection_response = test_client.post(
        "/api/collections",
        json={
            "name": "Backup export",
            "description": "Collection backup target",
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

    assets = AssetRepository().list_assets(collection_id=collection_id)
    assert len(assets) == 2
    Path(assets[0].local_original_path).unlink()

    export_response = test_client.get(f"/api/backup/collections/{collection_id}/export")
    assert export_response.status_code == 200

    names, manifest = _read_zip_entries(export_response.content)
    assert "collection-export-manifest.json" in names
    image_entries = [name for name in names if name != "collection-export-manifest.json"]
    assert len(image_entries) == 1
    assert manifest["type"] == "collection-export"
    assert manifest["collection"]["id"] == collection_id
    assert manifest["exported_count"] == 1
    assert manifest["skipped_count"] == 1
    assert manifest["skipped_files"][0]["reason"] == "Original file is missing from managed storage."


def test_collection_export_fails_when_no_exportable_files_remain(test_client: TestClient) -> None:
    collection_response = test_client.post(
        "/api/collections",
        json={
            "name": "Missing originals",
            "description": "Should fail when all originals are gone",
            "source_id": "default-local-files",
            "is_active": True,
        },
    )
    assert collection_response.status_code == 201
    collection_id = collection_response.json()["id"]

    upload_response = test_client.post(
        "/api/assets/upload",
        data={"collection_id": collection_id},
        files=[("files", _image_upload("lost.jpg", (0, 0, 255)))],
    )
    assert upload_response.status_code == 201

    assets = AssetRepository().list_assets(collection_id=collection_id)
    assert len(assets) == 1
    Path(assets[0].local_original_path).unlink()

    export_response = test_client.get(f"/api/backup/collections/{collection_id}/export")
    assert export_response.status_code == 400
    assert export_response.json()["detail"] == "Collection has no exportable original files."

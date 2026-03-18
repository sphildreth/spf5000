from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from tempfile import NamedTemporaryFile
from typing import BinaryIO
from uuid import uuid4
from zipfile import BadZipFile, ZIP_DEFLATED, ZipFile

from fastapi import FastAPI

from app.core.config import settings
from app.db.bootstrap import initialize_runtime
from app.db.connection import decentdb, exclusive_database_access, get_connection, is_null_connection, reset_connection_state
from app.repositories.asset_repository import AssetRepository
from app.repositories.collection_repository import CollectionRepository
from app.runtime_coordinators import start_background_coordinators, stop_background_coordinators

_BACKUP_DATABASE_MEMBER = "spf5000.ddb"
_BACKUP_MANIFEST_MEMBER = "backup-manifest.json"
_COLLECTION_MANIFEST_MEMBER = "collection-export-manifest.json"
_EXPORT_MEDIA_TYPE = "application/zip"


@dataclass(slots=True)
class GeneratedArchive:
    path: Path
    filename: str
    media_type: str = _EXPORT_MEDIA_TYPE


@dataclass(slots=True)
class DatabaseRestoreResult:
    restored: bool
    reauthenticate_required: bool
    media_restored: bool
    message: str


class BackupService:
    def __init__(
        self,
        collection_repo: CollectionRepository | None = None,
        asset_repo: AssetRepository | None = None,
    ) -> None:
        self.collection_repo = collection_repo or CollectionRepository()
        self.asset_repo = asset_repo or AssetRepository()

    def export_database_archive(self) -> GeneratedArchive:
        created_at = self._timestamp_iso()
        archive_filename = f"spf5000-database-backup-{self._timestamp_slug()}.zip"
        archive_path = self._create_export_path(archive_filename)
        snapshot_path = self._create_export_path(f"spf5000-database-snapshot-{uuid4().hex[:8]}.ddb")

        try:
            with exclusive_database_access():
                self._save_database_snapshot(snapshot_path)

            manifest = {
                "type": "database-backup",
                "created_at": created_at,
                "database_filename": _BACKUP_DATABASE_MEMBER,
                "database_size_bytes": snapshot_path.stat().st_size,
                "media_included": False,
                "files": [_BACKUP_DATABASE_MEMBER, _BACKUP_MANIFEST_MEMBER],
            }

            with ZipFile(archive_path, mode="w", compression=ZIP_DEFLATED) as archive:
                archive.write(snapshot_path, arcname=_BACKUP_DATABASE_MEMBER)
                archive.writestr(_BACKUP_MANIFEST_MEMBER, json.dumps(manifest, indent=2, sort_keys=True))
        except Exception:
            if archive_path.exists():
                archive_path.unlink()
            raise
        finally:
            if snapshot_path.exists():
                snapshot_path.unlink()

        return GeneratedArchive(path=archive_path, filename=archive_filename)

    def restore_database_archive(self, archive_file: BinaryIO, app: FastAPI) -> DatabaseRestoreResult:
        database_bytes = self._read_database_backup_bytes(archive_file)
        restore_dir = settings.staging_dir / "backup-restore"
        restore_dir.mkdir(parents=True, exist_ok=True)

        temp_candidate_path: Path | None = None
        try:
            with NamedTemporaryFile(
                mode="wb",
                dir=restore_dir,
                prefix=f"database-restore-{uuid4().hex[:8]}-",
                suffix=".ddb",
                delete=False,
            ) as handle:
                handle.write(database_bytes)
                temp_candidate_path = Path(handle.name)

            if temp_candidate_path.stat().st_size <= 0:
                raise ValueError("Backup archive contains an empty database file.")
            self._validate_candidate_database(temp_candidate_path)

            stop_background_coordinators(app)
            try:
                with exclusive_database_access():
                    reset_connection_state()
                    self._remove_database_sidecars()
                    settings.database_path.parent.mkdir(parents=True, exist_ok=True)
                    os.replace(temp_candidate_path, settings.database_path)
                    temp_candidate_path = None
                    self._remove_database_sidecars()
                    initialize_runtime()
                    reset_connection_state()
            finally:
                start_background_coordinators(app)
        finally:
            if temp_candidate_path is not None and temp_candidate_path.exists():
                temp_candidate_path.unlink()

        return DatabaseRestoreResult(
            restored=True,
            reauthenticate_required=True,
            media_restored=False,
            message="Database restored successfully. Media files were not restored. Please sign in again.",
        )

    def export_collection_archive(self, collection_id: str) -> GeneratedArchive:
        collection = self.collection_repo.get_collection(collection_id)
        if collection is None:
            raise LookupError("Collection not found.")

        assets = self.asset_repo.list_assets(collection_id=collection_id)
        created_at = self._timestamp_iso()
        archive_filename = f"spf5000-collection-{self._slugify(collection.name)}-{self._timestamp_slug()}.zip"
        archive_path = self._create_export_path(archive_filename)
        skipped_files: list[dict[str, object]] = []
        exported_files: list[dict[str, object]] = []
        used_names: set[str] = set()
        originals_root = settings.originals_dir.resolve()

        try:
            with ZipFile(archive_path, mode="w", compression=ZIP_DEFLATED) as archive:
                for asset in assets:
                    exportable_path, skip_reason = self._resolve_exportable_original(asset.local_original_path, originals_root)
                    if exportable_path is None:
                        skipped_files.append(
                            {
                                "asset_id": asset.id,
                                "original_filename": asset.original_filename,
                                "reason": skip_reason,
                            }
                        )
                        continue

                    archive_name = self._unique_archive_name(asset.original_filename or exportable_path.name, used_names)
                    archive.write(exportable_path, arcname=archive_name)
                    exported_files.append(
                        {
                            "asset_id": asset.id,
                            "archive_name": archive_name,
                            "original_filename": asset.original_filename,
                            "checksum_sha256": asset.checksum_sha256,
                            "size_bytes": exportable_path.stat().st_size,
                        }
                    )

                if not exported_files:
                    raise ValueError("Collection has no exportable original files.")

                manifest = {
                    "type": "collection-export",
                    "created_at": created_at,
                    "collection": {
                        "id": collection.id,
                        "name": collection.name,
                        "description": collection.description,
                    },
                    "exported_count": len(exported_files),
                    "skipped_count": len(skipped_files),
                    "exported_files": exported_files,
                    "skipped_files": skipped_files,
                }
                archive.writestr(_COLLECTION_MANIFEST_MEMBER, json.dumps(manifest, indent=2, sort_keys=True))
        except Exception:
            if archive_path.exists():
                archive_path.unlink()
            raise

        return GeneratedArchive(path=archive_path, filename=archive_filename)

    @staticmethod
    def cleanup_archive(path: Path) -> None:
        if path.exists():
            path.unlink()

    def _read_database_backup_bytes(self, archive_file: BinaryIO) -> bytes:
        try:
            archive_file.seek(0)
        except Exception:  # pragma: no cover - UploadFile file handles are seekable in normal operation.
            pass

        try:
            with ZipFile(archive_file) as archive:
                self._validate_database_archive(archive)
                return archive.read(_BACKUP_DATABASE_MEMBER)
        except BadZipFile as exc:
            raise ValueError("Uploaded file is not a valid ZIP archive.") from exc
        except KeyError as exc:
            raise ValueError("Backup archive is missing required files.") from exc

    def _validate_database_archive(self, archive: ZipFile) -> None:
        names = [info.filename for info in archive.infolist()]
        if not names:
            raise ValueError("Backup archive is empty.")

        for name in names:
            self._validate_archive_member_name(name)

        self._require_single_member(archive, _BACKUP_DATABASE_MEMBER)
        self._require_single_member(archive, _BACKUP_MANIFEST_MEMBER)

        database_info = archive.getinfo(_BACKUP_DATABASE_MEMBER)
        if database_info.is_dir() or database_info.file_size <= 0:
            raise ValueError("Backup archive contains an invalid database file.")

        manifest = self._read_json_member(archive, _BACKUP_MANIFEST_MEMBER, error_prefix="Backup manifest")
        if manifest.get("type") != "database-backup":
            raise ValueError("Backup manifest type must be 'database-backup'.")
        if manifest.get("database_filename") != _BACKUP_DATABASE_MEMBER:
            raise ValueError("Backup manifest references an unexpected database filename.")

    @staticmethod
    def _require_single_member(archive: ZipFile, expected_name: str) -> None:
        matches = [info for info in archive.infolist() if info.filename == expected_name]
        if not matches:
            raise ValueError(f"Backup archive must include {expected_name}.")
        if len(matches) > 1:
            raise ValueError(f"Backup archive contains duplicate {expected_name} entries.")

    @staticmethod
    def _read_json_member(archive: ZipFile, member_name: str, *, error_prefix: str) -> dict[str, object]:
        try:
            raw = archive.read(member_name)
        except KeyError as exc:
            raise ValueError(f"{error_prefix} is missing.") from exc
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError(f"{error_prefix} must be valid UTF-8 JSON.") from exc
        if not isinstance(payload, dict):
            raise ValueError(f"{error_prefix} must be a JSON object.")
        return payload

    @staticmethod
    def _validate_archive_member_name(name: str) -> None:
        path = PurePosixPath(name)
        if not name or path.is_absolute() or ".." in path.parts:
            raise ValueError("Backup archive contains an invalid member path.")

    @staticmethod
    def _resolve_exportable_original(local_original_path: str, originals_root: Path) -> tuple[Path | None, str | None]:
        try:
            resolved = Path(local_original_path).resolve(strict=True)
        except FileNotFoundError:
            return None, "Original file is missing from managed storage."
        except OSError:
            return None, "Original file path is invalid."

        if not resolved.is_file():
            return None, "Original file is not a regular file."

        try:
            resolved.relative_to(originals_root)
        except ValueError:
            return None, "Original file is outside managed originals storage."

        return resolved, None

    @staticmethod
    def _unique_archive_name(preferred_name: str, used_names: set[str]) -> str:
        candidate_path = PurePosixPath(preferred_name)
        stem = candidate_path.stem or "image"
        suffix = candidate_path.suffix
        base_name = candidate_path.name if candidate_path.name not in {"", "."} else f"{stem}{suffix}"
        sanitized = Path(base_name).name or f"{stem}{suffix}"
        candidate = sanitized
        counter = 1
        while candidate in used_names:
            candidate = f"{Path(sanitized).stem}-{counter}{Path(sanitized).suffix}"
            counter += 1
        used_names.add(candidate)
        return candidate

    def _create_export_path(self, filename: str) -> Path:
        export_dir = settings.staging_dir / "exports"
        export_dir.mkdir(parents=True, exist_ok=True)
        return export_dir / filename

    def _save_database_snapshot(self, snapshot_path: Path) -> None:
        reset_connection_state()
        with get_connection() as conn:
            if is_null_connection(conn) or decentdb is None:
                raise FileNotFoundError("Database file is unavailable.")
            conn.checkpoint()
            conn.save_as(str(snapshot_path))
        reset_connection_state()

    @staticmethod
    def _remove_database_sidecars() -> None:
        for suffix in ("-wal", "-shm"):
            sidecar_path = Path(f"{settings.database_path}{suffix}")
            if sidecar_path.exists():
                sidecar_path.unlink()

    @staticmethod
    def _validate_candidate_database(candidate_path: Path) -> None:
        if decentdb is None:
            raise RuntimeError("Database restore is unavailable because DecentDB is not installed.")

        try:
            conn = decentdb.connect(str(candidate_path))
            try:
                tables = set(conn.list_tables())
            finally:
                conn.close()
        except Exception as exc:
            raise ValueError("Backup archive contains an invalid SPF5000 database file.") from exc
        required_tables = {"settings", "admin_users", "collections"}
        if not required_tables.issubset(tables):
            raise ValueError("Backup archive does not contain a recognizable SPF5000 database.")

    @staticmethod
    def _slugify(value: str) -> str:
        slug = "-".join(part for part in "".join(ch.lower() if ch.isalnum() else "-" for ch in value).split("-") if part)
        return slug or "collection"

    @staticmethod
    def _timestamp_slug() -> str:
        return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    @staticmethod
    def _timestamp_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

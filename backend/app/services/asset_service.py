from __future__ import annotations

import structlog
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Sequence
from uuid import uuid4

from fastapi import UploadFile
from PIL import UnidentifiedImageError

from app.core.config import settings
from app.db.bootstrap import DEFAULT_COLLECTION_ID, DEFAULT_SOURCE_ID
from app.models.asset import Asset, AssetVariant
from app.models.asset_upload import AssetUploadSummary
from app.repositories.asset_repository import AssetRepository
from app.repositories.base import utc_now
from app.repositories.collection_repository import CollectionRepository
from app.repositories.source_repository import SourceRepository
from app.services.asset_ingest_service import AssetIngestService

LOGGER = structlog.get_logger(__name__)


@dataclass(slots=True)
class BulkRemoveSummary:
    removed_count: int
    deactivated_count: int
    errors: list[dict[str, str]] = field(default_factory=list)


class AssetService:
    def __init__(
        self,
        repo: AssetRepository | None = None,
        source_repo: SourceRepository | None = None,
        collection_repo: CollectionRepository | None = None,
        ingest_service: AssetIngestService | None = None,
    ) -> None:
        self.repo = repo or AssetRepository()
        self.source_repo = source_repo or SourceRepository()
        self.collection_repo = collection_repo or CollectionRepository()
        self.ingest_service = ingest_service or AssetIngestService()

    def list_assets(self, collection_id: str | None = None) -> list[Asset]:
        return self.repo.list_assets(collection_id=collection_id)

    def get_asset(self, asset_id: str) -> Asset | None:
        return self.repo.get_asset(asset_id)

    def get_variant(self, asset_id: str, kind: str) -> AssetVariant | None:
        asset = self.repo.get_asset(asset_id)
        if asset is None:
            return None
        if kind == "original":
            return AssetVariant(
                id=f"{asset.id}-original",
                asset_id=asset.id,
                kind="original",
                local_path=asset.local_original_path,
                mime_type=asset.mime_type,
                width=asset.width,
                height=asset.height,
                size_bytes=asset.size_bytes,
                created_at=asset.created_at,
            )
        return self.repo.get_variant(asset_id, kind)

    def get_variant_path(self, asset_id: str, kind: str) -> tuple[Path, str] | None:
        variant = self.get_variant(asset_id, kind)
        if variant is None:
            return None
        path = Path(variant.local_path)
        if not path.exists():
            return None
        return path, variant.mime_type

    def remove_from_collection(self, asset_id: str, collection_id: str) -> None:
        asset_id = asset_id.strip()
        collection_id = collection_id.strip()
        asset = self.repo.get_asset(asset_id)
        if asset is None:
            raise LookupError("Asset not found.")

        collection = self.collection_repo.get_collection(collection_id)
        if collection is None:
            raise LookupError("Collection not found.")

        if collection_id not in asset.collection_ids:
            raise ValueError("Asset is not assigned to the specified collection.")

        self.repo.remove_asset_from_collection(asset_id, collection_id)
        self.repo.deactivate_asset_if_unassigned(asset_id)

    def bulk_remove_from_collection(
        self, collection_id: str, asset_ids: list[str]
    ) -> BulkRemoveSummary:
        collection_id = collection_id.strip()
        normalized_asset_ids = self._normalize_asset_ids(asset_ids)
        if not collection_id:
            raise ValueError("Collection ID is required.")
        if not normalized_asset_ids:
            raise ValueError("Select at least one photo to remove.")

        collection = self.collection_repo.get_collection(collection_id)
        if collection is None:
            raise LookupError("Collection not found.")

        removed_count = 0
        deactivated_count = 0
        errors: list[dict[str, str]] = []

        for asset_id in normalized_asset_ids:
            asset = self.repo.get_asset(asset_id)
            if asset is None:
                errors.append({"asset_id": asset_id, "reason": "Asset not found."})
                continue
            if collection_id not in asset.collection_ids:
                errors.append(
                    {
                        "asset_id": asset_id,
                        "reason": "Asset is not assigned to the specified collection.",
                    }
                )
                continue
            remaining = [cid for cid in asset.collection_ids if cid != collection_id]
            self.repo.remove_asset_from_collection(asset_id, collection_id)
            self.repo.deactivate_asset_if_unassigned(asset_id)
            removed_count += 1
            if not remaining:
                deactivated_count += 1

        return BulkRemoveSummary(
            removed_count=removed_count,
            deactivated_count=deactivated_count,
            errors=errors,
        )

    def upload_files(
        self, files: Sequence[UploadFile], collection_id: str | None = None
    ) -> AssetUploadSummary:
        if not files:
            raise ValueError("Select at least one image to upload.")

        source = self._get_local_upload_source()
        target_collection_id = collection_id or DEFAULT_COLLECTION_ID
        target_collection = self.collection_repo.get_collection(target_collection_id)
        if target_collection is None:
            raise ValueError("Collection not found.")
        if target_collection.source_id not in {None, source.id}:
            raise ValueError("Uploads can only target local or shared collections.")

        staging_dir = settings.import_staging_dir / "admin-uploads"
        staging_dir.mkdir(parents=True, exist_ok=True)

        summary = AssetUploadSummary(
            source_id=source.id,
            collection_id=target_collection.id,
            received_count=len(files),
            imported_count=0,
            duplicate_count=0,
            error_count=0,
        )

        for index, upload in enumerate(files, start=1):
            original_filename = Path(upload.filename or "").name or f"upload-{index}"
            extension = Path(original_filename).suffix.lower()
            if extension and extension not in settings.supported_image_extensions:
                summary.error_count += 1
                summary.errors.append(
                    f"{original_filename}: unsupported file type; supported formats are "
                    f"{', '.join(settings.supported_image_extensions)}."
                )
                upload.file.close()
                continue

            staged_path: Path | None = None
            try:
                staged_path = self._write_upload_to_staging(
                    upload, staging_dir, suffix=extension or ".upload"
                )
                result = self.ingest_service.ingest_file(
                    source_id=source.id,
                    collection_ids=[target_collection.id],
                    source_path=staged_path,
                    imported_from_path=f"admin-upload:{original_filename}",
                    original_filename=original_filename,
                    metadata={"uploaded_via": "admin_ui"},
                )
                if result.created:
                    summary.imported_count += 1
                else:
                    summary.duplicate_count += 1
            except Exception as exc:  # noqa: BLE001 - surfacing per-file errors is intentional.
                LOGGER.exception(
                    "asset_upload_import_failed", original_filename=original_filename
                )
                summary.error_count += 1
                summary.errors.append(
                    f"{original_filename}: {self._describe_upload_error(exc)}"
                )
            finally:
                upload.file.close()
                if staged_path is not None and staged_path.exists():
                    staged_path.unlink()

        if summary.imported_count > 0 or summary.duplicate_count > 0:
            self.source_repo.touch_last_import(source.id, utc_now())

        return summary

    def _get_local_upload_source(self):
        source = self.source_repo.get_source(DEFAULT_SOURCE_ID)
        if source is not None and source.provider_type == "local_files":
            return source

        for candidate in self.source_repo.list_sources():
            if candidate.provider_type == "local_files":
                return candidate

        raise RuntimeError("No local upload source is configured.")

    @staticmethod
    def _write_upload_to_staging(
        upload: UploadFile, staging_dir: Path, *, suffix: str
    ) -> Path:
        upload.file.seek(0)
        with NamedTemporaryFile(
            mode="wb",
            dir=staging_dir,
            prefix=f"upload-{uuid4().hex[:8]}-",
            suffix=suffix,
            delete=False,
        ) as handle:
            shutil.copyfileobj(upload.file, handle)
            return Path(handle.name)

    @staticmethod
    def _describe_upload_error(exc: Exception) -> str:
        if isinstance(exc, UnidentifiedImageError):
            return "the file could not be read as a supported image"
        message = str(exc).strip()
        return message or "the file could not be imported"

    @staticmethod
    def _normalize_asset_ids(asset_ids: Sequence[str]) -> list[str]:
        normalized: list[str] = []
        seen: set[str] = set()
        for asset_id in asset_ids:
            candidate = asset_id.strip()
            if not candidate or candidate in seen:
                continue
            normalized.append(candidate)
            seen.add(candidate)
        return normalized

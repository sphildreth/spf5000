from __future__ import annotations

import hashlib
import logging
import shutil
from pathlib import Path
from uuid import uuid4

from PIL import Image, ImageOps

from app.core.config import settings
from app.models.asset import Asset, AssetVariant
from app.models.import_job import ImportJob
from app.providers.base import DiscoveredImage, ProviderScanResult
from app.repositories.asset_repository import AssetRepository
from app.repositories.base import json_dumps, utc_now
from app.repositories.import_repository import ImportRepository
from app.repositories.settings_repository import SettingsRepository
from app.repositories.source_repository import SourceRepository
from app.services.source_service import SourceService

LOGGER = logging.getLogger(__name__)


class ImportService:
    def __init__(
        self,
        asset_repo: AssetRepository | None = None,
        import_repo: ImportRepository | None = None,
        source_repo: SourceRepository | None = None,
        source_service: SourceService | None = None,
        settings_repo: SettingsRepository | None = None,
    ) -> None:
        self.asset_repo = asset_repo or AssetRepository()
        self.import_repo = import_repo or ImportRepository()
        self.source_repo = source_repo or SourceRepository()
        self.source_service = source_service or SourceService(repo=self.source_repo)
        self.settings_repo = settings_repo or SettingsRepository()

    def scan_local_source(self, source_id: str, max_samples: int = 10) -> tuple[ImportJob, ProviderScanResult]:
        source = self.source_service.get_source(source_id)
        if source is None:
            raise ValueError(f"Unknown source: {source_id}")
        provider = self.source_service.get_provider(source.provider_type)
        scan_result = provider.scan_directory(source.import_path)
        now = utc_now()
        job = ImportJob(
            id=f"scan-{uuid4().hex}",
            job_type="scan",
            status="completed",
            source_id=source.id,
            collection_id=None,
            import_path=scan_result.import_path,
            discovered_count=scan_result.discovered_count,
            imported_count=0,
            duplicate_count=0,
            skipped_count=scan_result.ignored_count,
            error_count=0,
            sample_filenames=[item.filename for item in scan_result.discovered[:max_samples]],
            message=f"Scanned {scan_result.discovered_count} supported files",
            started_at=now,
            completed_at=now,
        )
        stored_job = self.import_repo.create_job(job)
        self.source_repo.touch_last_scan(source.id, now)
        return stored_job, scan_result

    def import_local_source(self, source_id: str, collection_id: str, max_samples: int = 10) -> ImportJob:
        source = self.source_service.get_source(source_id)
        if source is None:
            raise ValueError(f"Unknown source: {source_id}")
        provider = self.source_service.get_provider(source.provider_type)
        scan_result = provider.scan_directory(source.import_path)
        started_at = utc_now()
        job = ImportJob(
            id=f"import-{uuid4().hex}",
            job_type="import",
            status="running",
            source_id=source.id,
            collection_id=collection_id,
            import_path=scan_result.import_path,
            discovered_count=scan_result.discovered_count,
            imported_count=0,
            duplicate_count=0,
            skipped_count=scan_result.ignored_count,
            error_count=0,
            sample_filenames=[item.filename for item in scan_result.discovered[:max_samples]],
            message="Import in progress",
            started_at=started_at,
            completed_at=None,
        )
        self.import_repo.create_job(job)

        for candidate in scan_result.discovered:
            try:
                checksum = self._sha256_file(Path(candidate.path))
                existing = self.asset_repo.find_by_checksum(checksum)
                if existing is not None:
                    self.asset_repo.add_asset_to_collection(existing.id, collection_id)
                    job.duplicate_count += 1
                    continue
                asset = self._materialize_asset(source.id, collection_id, candidate, checksum)
                self.asset_repo.create_asset(asset)
                job.imported_count += 1
            except Exception as exc:  # pragma: no cover
                LOGGER.exception("Failed to import %s", candidate.path)
                job.error_count += 1
                job.message = f"Import completed with {job.error_count} errors"
                LOGGER.error("Import error: %s", exc)

        job.status = "completed" if job.error_count == 0 else "completed_with_errors"
        job.message = (
            f"Imported {job.imported_count} new assets, {job.duplicate_count} duplicates, {job.error_count} errors"
        )
        job.completed_at = utc_now()
        self.source_repo.touch_last_scan(source.id, job.completed_at)
        self.source_repo.touch_last_import(source.id, job.completed_at)
        return self.import_repo.update_job(job)

    def get_latest_job(self) -> ImportJob | None:
        return self.import_repo.get_latest_job()

    def _materialize_asset(self, source_id: str, collection_id: str, candidate: DiscoveredImage, checksum: str) -> Asset:
        source_path = Path(candidate.path)
        device_settings = self.settings_repo.get_settings()
        original_destination = self._build_managed_path(settings.originals_dir, checksum, source_path.suffix.lower())
        original_destination.parent.mkdir(parents=True, exist_ok=True)
        if not original_destination.exists():
            shutil.copy2(source_path, original_destination)

        with Image.open(original_destination) as image:
            normalized = ImageOps.exif_transpose(image)
            width, height = normalized.size
            image_format = image.format or normalized.format or "JPEG"
            mime_type = Image.MIME.get(image_format, "image/jpeg")
            metadata = {
                "format": image_format,
                "mode": normalized.mode,
                "width": width,
                "height": height,
            }
            thumbnail_variant = self._generate_variant(
                normalized,
                checksum=checksum,
                kind="thumbnail",
                max_width=device_settings.thumbnail_max_size,
                max_height=device_settings.thumbnail_max_size,
            )
            display_variant = self._generate_variant(
                normalized,
                checksum=checksum,
                kind="display",
                max_width=device_settings.display_variant_width,
                max_height=device_settings.display_variant_height,
            )

        now = utc_now()
        return Asset(
            id=f"asset-{checksum[:24]}",
            source_id=source_id,
            checksum_sha256=checksum,
            filename=source_path.stem,
            original_filename=source_path.name,
            original_extension=source_path.suffix.lower(),
            mime_type=mime_type,
            width=width,
            height=height,
            size_bytes=original_destination.stat().st_size,
            imported_from_path=str(source_path),
            local_original_path=str(original_destination),
            metadata_json=json_dumps(metadata),
            created_at=now,
            updated_at=now,
            imported_at=now,
            is_active=True,
            collection_ids=[collection_id],
            variants=[thumbnail_variant, display_variant],
        )

    def _generate_variant(
        self,
        image: Image.Image,
        *,
        checksum: str,
        kind: str,
        max_width: int,
        max_height: int,
    ) -> AssetVariant:
        target_dir = settings.thumbnails_dir if kind == "thumbnail" else settings.display_variants_dir
        destination = self._build_managed_path(target_dir, checksum, ".jpg")
        destination.parent.mkdir(parents=True, exist_ok=True)

        working = image.copy()
        working.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
        rendered = self._to_rgb(working)
        rendered.save(destination, format="JPEG", quality=settings.jpeg_quality, optimize=True)
        now = utc_now()
        return AssetVariant(
            id=f"variant-{kind}-{checksum[:24]}",
            asset_id=f"asset-{checksum[:24]}",
            kind=kind,
            local_path=str(destination),
            mime_type="image/jpeg",
            width=rendered.width,
            height=rendered.height,
            size_bytes=destination.stat().st_size,
            created_at=now,
        )

    @staticmethod
    def _build_managed_path(base_dir: Path, checksum: str, extension: str) -> Path:
        return base_dir / checksum[:2] / f"{checksum}{extension}"

    @staticmethod
    def _to_rgb(image: Image.Image) -> Image.Image:
        if image.mode == "RGB":
            return image
        if image.mode in {"RGBA", "LA"}:
            background = Image.new("RGB", image.size, (0, 0, 0))
            background.paste(image, mask=image.getchannel("A"))
            return background
        return image.convert("RGB")

    @staticmethod
    def _sha256_file(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

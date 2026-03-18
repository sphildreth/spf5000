from __future__ import annotations

import hashlib
import structlog
import math
import shutil
from dataclasses import dataclass
from pathlib import Path

import decentdb  # type: ignore[attr-defined, no-redef]
from PIL import Image, ImageOps

from app.core.config import settings
from app.models.asset import Asset, AssetVariant
from app.repositories.asset_repository import AssetRepository
from app.repositories.base import json_dumps, utc_now
from app.repositories.settings_repository import SettingsRepository
from app.services.background_service import derive_background_meta

LOGGER = structlog.get_logger(__name__)


@dataclass(slots=True)
class AssetIngestResult:
    asset: Asset
    created: bool
    checksum_sha256: str


class AssetIngestService:
    def __init__(
        self,
        asset_repo: AssetRepository | None = None,
        settings_repo: SettingsRepository | None = None,
    ) -> None:
        self.asset_repo = asset_repo or AssetRepository()
        self.settings_repo = settings_repo or SettingsRepository()

    def ingest_file(
        self,
        *,
        source_id: str,
        collection_ids: list[str],
        source_path: Path,
        imported_from_path: str,
        original_filename: str | None = None,
        metadata: dict[str, object] | None = None,
    ) -> AssetIngestResult:
        checksum = self._sha256_file(source_path)
        existing = self.asset_repo.find_by_checksum(checksum)
        if existing is not None:
            for collection_id in collection_ids:
                self.asset_repo.add_asset_to_collection(existing.id, collection_id)
            return AssetIngestResult(
                asset=existing, created=False, checksum_sha256=checksum
            )

        asset = self._materialize_asset(
            source_id=source_id,
            source_path=source_path,
            imported_from_path=imported_from_path,
            original_filename=original_filename,
            checksum=checksum,
            collection_ids=collection_ids,
            metadata=metadata or {},
        )
        try:
            created_asset = self.asset_repo.create_asset(asset)
            return AssetIngestResult(
                asset=created_asset, created=True, checksum_sha256=checksum
            )
        except decentdb.IntegrityError:
            LOGGER.debug("asset_ingest_race_deduped", checksum_prefix=checksum[:16])
            existing = self.asset_repo.find_by_checksum(checksum)
            if existing is not None:
                for collection_id in collection_ids:
                    self.asset_repo.add_asset_to_collection(existing.id, collection_id)
                return AssetIngestResult(
                    asset=existing, created=False, checksum_sha256=checksum
                )
            raise

    def _materialize_asset(
        self,
        *,
        source_id: str,
        source_path: Path,
        imported_from_path: str,
        original_filename: str | None,
        checksum: str,
        collection_ids: list[str],
        metadata: dict[str, object],
    ) -> Asset:
        device_settings = self.settings_repo.get_settings()
        filename = original_filename or source_path.name
        extension = (
            Path(filename).suffix.lower() or source_path.suffix.lower() or ".jpg"
        )
        original_destination = self._build_managed_path(
            settings.originals_dir, checksum, extension
        )
        original_destination.parent.mkdir(parents=True, exist_ok=True)
        if source_path.resolve() != original_destination.resolve():
            if not original_destination.exists():
                shutil.copy2(source_path, original_destination)
        elif not original_destination.exists():
            original_destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_path, original_destination)

        original_image: Image.Image | None = None
        normalized: Image.Image | None = None
        try:
            original_image = Image.open(original_destination)
            normalized = ImageOps.exif_transpose(original_image)
            width, height = normalized.size
            image_format = original_image.format or normalized.format or "JPEG"
            mime_type = Image.MIME.get(image_format, "image/jpeg")
            complete_metadata = {
                "format": image_format,
                "mode": normalized.mode,
                "width": width,
                "height": height,
                **metadata,
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
            background_metadata = self._derive_background_metadata(display_variant)
            if background_metadata is not None:
                complete_metadata["background"] = background_metadata
        finally:
            if normalized is not None and normalized is not original_image:
                normalized.close()
            if original_image is not None:
                original_image.close()

        now = utc_now()
        original_name = Path(filename).name
        return Asset(
            id=f"asset-{checksum[:24]}",
            source_id=source_id,
            checksum_sha256=checksum,
            filename=Path(original_name).stem,
            original_filename=original_name,
            original_extension=extension,
            mime_type=mime_type,
            width=width,
            height=height,
            size_bytes=original_destination.stat().st_size,
            imported_from_path=imported_from_path,
            local_original_path=str(original_destination),
            metadata_json=json_dumps(complete_metadata),
            created_at=now,
            updated_at=now,
            imported_at=now,
            is_active=True,
            collection_ids=collection_ids,
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
        target_dir = (
            settings.thumbnails_dir
            if kind == "thumbnail"
            else settings.display_variants_dir
        )
        destination = self._build_managed_path(target_dir, checksum, ".jpg")
        destination.parent.mkdir(parents=True, exist_ok=True)

        working: Image.Image | None = None
        rendered: Image.Image | None = None
        width, height = 0, 0
        try:
            if kind == "display":
                working = self._resize_display_variant(
                    image, max_width=max_width, max_height=max_height
                )
            else:
                working = image.copy()
                working.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)

            rendered = self._to_rgb(working)
            rendered.save(
                destination, format="JPEG", quality=settings.jpeg_quality, optimize=True
            )
            width, height = rendered.size
        finally:
            if rendered is not None and rendered is not working:
                rendered.close()
            if working is not None and working is not image:
                working.close()

        now = utc_now()
        return AssetVariant(
            id=f"variant-{kind}-{checksum[:24]}",
            asset_id=f"asset-{checksum[:24]}",
            kind=kind,
            local_path=str(destination),
            mime_type="image/jpeg",
            width=width,
            height=height,
            size_bytes=destination.stat().st_size,
            created_at=now,
        )

    def _derive_background_metadata(
        self, display_variant: AssetVariant
    ) -> dict[str, object] | None:
        try:
            background = derive_background_meta(Path(display_variant.local_path))
        except Exception:
            LOGGER.warning(
                "background_derivation_failed",
                variant_path=str(display_variant.local_path),
                exc_info=True,
            )
            return None
        return {
            "dominant_color": background.dominant_color,
            "gradient_colors": background.gradient_colors,
        }

    @staticmethod
    def _build_managed_path(base_dir: Path, checksum: str, extension: str) -> Path:
        return base_dir / checksum[:2] / f"{checksum}{extension}"

    @staticmethod
    def _resize_display_variant(
        image: Image.Image, *, max_width: int, max_height: int
    ) -> Image.Image:
        width, height = image.size
        if width <= 0 or height <= 0:
            return image.copy()

        scale = min(1.0, max(max_width / width, max_height / height))
        if scale >= 1.0:
            return image.copy()

        resized_width = max(1, math.ceil(width * scale))
        resized_height = max(1, math.ceil(height * scale))
        return image.resize((resized_width, resized_height), Image.Resampling.LANCZOS)

    @staticmethod
    def _to_rgb(image: Image.Image) -> Image.Image:
        if image.mode == "RGB":
            return image
        if image.mode in {"RGBA", "LA"}:
            background = Image.new("RGB", image.size, (0, 0, 0))
            alpha_mask = image.getchannel("A")
            background.paste(image, mask=alpha_mask)
            alpha_mask.close()
            return background
        return image.convert("RGB")

    @staticmethod
    def _sha256_file(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

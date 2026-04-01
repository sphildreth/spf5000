from __future__ import annotations

from typing import Iterator

from app.core.config import settings
from app.providers.base import DiscoveredImage, ProviderScanResult
from app.providers.google_photos.errors import GooglePhotosError
from app.providers.google_photos.metadata import PROVIDER_NAME


class GooglePhotosProvider:
    def provider_name(self) -> str:
        return PROVIDER_NAME

    def health_check(self, _import_path: str) -> dict[str, object]:
        return {
            "available": settings.google_photos_enabled,
            "configured": settings.google_photos_configured,
            "provider": PROVIDER_NAME,
            "display_name": settings.google_photos_provider_display_name,
            "import_path": str(settings.google_photos_import_dir),
        }

    def scan_directory(
        self, import_path: str, *, sample_limit: int | None = None
    ) -> ProviderScanResult:
        del sample_limit
        raise GooglePhotosError(
            f"{settings.google_photos_provider_display_name} does not support local directory scanning for {import_path!r}."
        )

    def iter_directory(self, import_path: str) -> Iterator[DiscoveredImage]:
        raise GooglePhotosError(
            f"{settings.google_photos_provider_display_name} does not support local directory scanning for {import_path!r}."
        )

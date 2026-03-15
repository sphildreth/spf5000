from __future__ import annotations

from pathlib import Path

from app.core.config import settings
from app.providers.base import DiscoveredImage, ProviderScanResult


class LocalFilesProvider:
    def provider_name(self) -> str:
        return "local_files"

    def health_check(self, import_path: str) -> dict[str, str | bool]:
        path = Path(import_path)
        return {
            "ok": path.exists() and path.is_dir(),
            "provider": self.provider_name(),
            "import_path": str(path),
        }

    def scan_directory(self, import_path: str) -> ProviderScanResult:
        root = Path(import_path)
        root.mkdir(parents=True, exist_ok=True)

        discovered: list[DiscoveredImage] = []
        ignored_count = 0
        supported_extensions = {extension.lower() for extension in settings.supported_image_extensions}

        for path in sorted(root.rglob("*")):
            if not path.is_file():
                continue
            if path.suffix.lower() not in supported_extensions:
                ignored_count += 1
                continue
            discovered.append(
                DiscoveredImage(
                    path=str(path),
                    filename=path.name,
                    extension=path.suffix.lower(),
                    size_bytes=path.stat().st_size,
                )
            )

        return ProviderScanResult(import_path=str(root), discovered=discovered, ignored_count=ignored_count)

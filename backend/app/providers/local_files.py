from __future__ import annotations

from pathlib import Path

from app.core.config import settings
from app.providers.base import DiscoveredImage, ProviderScanResult

_MAX_SCAN_DEPTH = 20
_MAX_FILES_PER_SCAN = 50_000


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
        root = Path(import_path).resolve()
        sources_root = settings.sources_root_dir.resolve()
        if not str(root).startswith(str(sources_root)):
            root.mkdir(parents=True, exist_ok=True)
            return ProviderScanResult(
                import_path=str(root), discovered=[], ignored_count=0
            )

        root.mkdir(parents=True, exist_ok=True)

        discovered: list[DiscoveredImage] = []
        ignored_count = 0
        supported_extensions = {
            extension.lower() for extension in settings.supported_image_extensions
        }

        for path in sorted(root.rglob("*")):
            if len(discovered) + ignored_count >= _MAX_FILES_PER_SCAN:
                break
            if not path.is_file():
                continue
            depth = len(path.relative_to(root).parts)
            if depth > _MAX_SCAN_DEPTH:
                ignored_count += 1
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

        return ProviderScanResult(
            import_path=str(root), discovered=discovered, ignored_count=ignored_count
        )

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator

from app.core.config import settings
from app.providers.base import DiscoveredImage, ProviderScanResult

_MAX_SCAN_DEPTH = 20
_MAX_FILES_PER_SCAN = 50_000


@dataclass(slots=True)
class LocalFilesWalk:
    root: Path
    supported_extensions: set[str]
    sample_limit: int | None = None
    discovered_count: int = 0
    ignored_count: int = 0
    discovered: list[DiscoveredImage] = field(default_factory=list)
    _consumed: bool = False

    def __iter__(self) -> Iterator[DiscoveredImage]:
        if self._consumed:
            return
        self._consumed = True

        for dirpath, dirnames, filenames in os.walk(self.root):
            current_dir = Path(dirpath)
            depth = len(current_dir.relative_to(self.root).parts)
            dirnames.sort()
            filenames.sort()

            if depth >= _MAX_SCAN_DEPTH - 1:
                dirnames[:] = []

            if depth >= _MAX_SCAN_DEPTH:
                self.ignored_count += len(filenames)
                if self.discovered_count + self.ignored_count >= _MAX_FILES_PER_SCAN:
                    break
                continue

            for filename in filenames:
                if self.discovered_count + self.ignored_count >= _MAX_FILES_PER_SCAN:
                    return

                path = current_dir / filename
                extension = path.suffix.lower()
                if extension not in self.supported_extensions:
                    self.ignored_count += 1
                    continue

                discovered = DiscoveredImage(
                    path=str(path),
                    filename=path.name,
                    extension=extension,
                    size_bytes=path.stat().st_size,
                )
                self.discovered_count += 1
                if self.sample_limit is None or len(self.discovered) < self.sample_limit:
                    self.discovered.append(discovered)
                yield discovered


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

    def scan_directory(
        self, import_path: str, *, sample_limit: int | None = None
    ) -> ProviderScanResult:
        root = Path(import_path).resolve()
        if not self._is_under_sources_root(root):
            root.mkdir(parents=True, exist_ok=True)
            return ProviderScanResult(
                import_path=str(root),
                discovered_count=0,
                ignored_count=0,
            )

        root.mkdir(parents=True, exist_ok=True)
        walk = self.walk_directory(import_path, sample_limit=sample_limit)
        for _ in walk:
            pass
        return ProviderScanResult(
            import_path=str(root),
            discovered_count=walk.discovered_count,
            ignored_count=walk.ignored_count,
            discovered=walk.discovered,
        )

    def iter_directory(self, import_path: str) -> Iterator[DiscoveredImage]:
        walk = self.walk_directory(import_path, sample_limit=0)
        yield from walk

    def walk_directory(
        self, import_path: str, *, sample_limit: int | None = None
    ) -> LocalFilesWalk:
        root = Path(import_path).resolve()
        if not self._is_under_sources_root(root):
            root.mkdir(parents=True, exist_ok=True)
            return LocalFilesWalk(root=root, supported_extensions=set(), sample_limit=0)

        root.mkdir(parents=True, exist_ok=True)
        supported_extensions = {
            extension.lower() for extension in settings.supported_image_extensions
        }
        return LocalFilesWalk(
            root=root,
            supported_extensions=supported_extensions,
            sample_limit=sample_limit,
        )

    @staticmethod
    def _is_under_sources_root(root: Path) -> bool:
        sources_root = settings.sources_root_dir.resolve()
        return str(root).startswith(str(sources_root))

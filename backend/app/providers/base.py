from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(slots=True)
class DiscoveredImage:
    path: str
    filename: str
    extension: str
    size_bytes: int


@dataclass(slots=True)
class ProviderScanResult:
    import_path: str
    discovered: list[DiscoveredImage]
    ignored_count: int

    @property
    def discovered_count(self) -> int:
        return len(self.discovered)


class PhotoProvider(Protocol):
    def provider_name(self) -> str: ...
    def health_check(self, import_path: str) -> dict[str, Any]: ...
    def scan_directory(self, import_path: str) -> ProviderScanResult: ...

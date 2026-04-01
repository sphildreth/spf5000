from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterator, Protocol


@dataclass(slots=True)
class DiscoveredImage:
    path: str
    filename: str
    extension: str
    size_bytes: int


@dataclass(slots=True)
class ProviderScanResult:
    import_path: str
    discovered_count: int
    ignored_count: int
    discovered: list[DiscoveredImage] = field(default_factory=list)


class PhotoProvider(Protocol):
    def provider_name(self) -> str: ...
    def health_check(self, import_path: str) -> dict[str, Any]: ...
    def scan_directory(
        self, import_path: str, *, sample_limit: int | None = None
    ) -> ProviderScanResult: ...
    def iter_directory(self, import_path: str) -> Iterator[DiscoveredImage]: ...

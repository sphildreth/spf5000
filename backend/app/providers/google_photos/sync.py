from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class GooglePhotosSyncStats:
    discovered_count: int = 0
    imported_count: int = 0
    duplicate_count: int = 0
    skipped_count: int = 0
    error_count: int = 0
    warnings: list[str] = field(default_factory=list)

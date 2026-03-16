from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class AssetUploadSummary:
    source_id: str
    collection_id: str
    received_count: int
    imported_count: int
    duplicate_count: int
    error_count: int
    errors: list[str] = field(default_factory=list)

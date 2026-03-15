from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class AssetVariant:
    id: str
    asset_id: str
    kind: str
    local_path: str
    mime_type: str
    width: int
    height: int
    size_bytes: int
    created_at: str


@dataclass(slots=True)
class Asset:
    id: str
    source_id: str
    checksum_sha256: str
    filename: str
    original_filename: str
    original_extension: str
    mime_type: str
    width: int
    height: int
    size_bytes: int
    imported_from_path: str
    local_original_path: str
    metadata_json: str
    created_at: str
    updated_at: str
    imported_at: str
    is_active: bool
    collection_ids: list[str] = field(default_factory=list)
    variants: list[AssetVariant] = field(default_factory=list)

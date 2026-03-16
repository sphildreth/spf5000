from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class AssetBackground:
    """Per-asset background fill metadata derived from the display variant.

    Colors are subdued/muted so they serve as tasteful letterbox fills that
    don't compete with the displayed photo.
    """

    dominant_color: str = ""       # CSS hex string, e.g. "#2a1e0c"
    gradient_colors: list[str] = field(default_factory=list)  # 2-element CSS hex list

    @property
    def ready(self) -> bool:
        return bool(self.dominant_color and len(self.gradient_colors) >= 2)


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

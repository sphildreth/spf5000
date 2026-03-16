from __future__ import annotations

import json

from pydantic import BaseModel

from app.models.asset import Asset, AssetVariant
from app.models.asset_upload import AssetUploadSummary


class AssetVariantResponse(BaseModel):
    kind: str
    url: str
    mime_type: str
    width: int
    height: int
    size_bytes: int

    @classmethod
    def from_domain(cls, asset_id: str, variant: AssetVariant) -> "AssetVariantResponse":
        return cls(
            kind=variant.kind,
            url=f"/api/assets/{asset_id}/variants/{variant.kind}",
            mime_type=variant.mime_type,
            width=variant.width,
            height=variant.height,
            size_bytes=variant.size_bytes,
        )


class AssetResponse(BaseModel):
    id: str
    source_id: str
    filename: str
    original_filename: str
    mime_type: str
    width: int
    height: int
    size_bytes: int
    checksum_sha256: str
    imported_from_path: str
    original_url: str
    thumbnail_url: str | None
    display_url: str | None
    collection_ids: list[str]
    metadata: dict[str, object]
    imported_at: str
    updated_at: str
    variants: list[AssetVariantResponse]

    @classmethod
    def from_domain(cls, asset: Asset) -> "AssetResponse":
        variants = [AssetVariantResponse.from_domain(asset.id, variant) for variant in asset.variants]
        thumbnail_variant = next((variant for variant in variants if variant.kind == "thumbnail"), None)
        display_variant = next((variant for variant in variants if variant.kind == "display"), None)
        return cls(
            id=asset.id,
            source_id=asset.source_id,
            filename=asset.filename,
            original_filename=asset.original_filename,
            mime_type=asset.mime_type,
            width=asset.width,
            height=asset.height,
            size_bytes=asset.size_bytes,
            checksum_sha256=asset.checksum_sha256,
            imported_from_path=asset.imported_from_path,
            original_url=f"/api/assets/{asset.id}/variants/original",
            thumbnail_url=None if thumbnail_variant is None else thumbnail_variant.url,
            display_url=None if display_variant is None else display_variant.url,
            collection_ids=asset.collection_ids,
            metadata=json.loads(asset.metadata_json),
            imported_at=asset.imported_at,
            updated_at=asset.updated_at,
            variants=variants,
        )


class AssetUploadResponse(BaseModel):
    source_id: str
    collection_id: str
    received_count: int
    imported_count: int
    duplicate_count: int
    error_count: int
    errors: list[str]

    @classmethod
    def from_domain(cls, summary: AssetUploadSummary) -> "AssetUploadResponse":
        return cls(
            source_id=summary.source_id,
            collection_id=summary.collection_id,
            received_count=summary.received_count,
            imported_count=summary.imported_count,
            duplicate_count=summary.duplicate_count,
            error_count=summary.error_count,
            errors=summary.errors,
        )

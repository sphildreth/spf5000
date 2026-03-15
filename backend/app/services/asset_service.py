from __future__ import annotations

from pathlib import Path

from app.models.asset import Asset, AssetVariant
from app.repositories.asset_repository import AssetRepository


class AssetService:
    def __init__(self, repo: AssetRepository | None = None) -> None:
        self.repo = repo or AssetRepository()

    def list_assets(self, collection_id: str | None = None) -> list[Asset]:
        return self.repo.list_assets(collection_id=collection_id)

    def get_asset(self, asset_id: str) -> Asset | None:
        return self.repo.get_asset(asset_id)

    def get_variant(self, asset_id: str, kind: str) -> AssetVariant | None:
        asset = self.repo.get_asset(asset_id)
        if asset is None:
            return None
        if kind == "original":
            return AssetVariant(
                id=f"{asset.id}-original",
                asset_id=asset.id,
                kind="original",
                local_path=asset.local_original_path,
                mime_type=asset.mime_type,
                width=asset.width,
                height=asset.height,
                size_bytes=asset.size_bytes,
                created_at=asset.created_at,
            )
        return self.repo.get_variant(asset_id, kind)

    def get_variant_path(self, asset_id: str, kind: str) -> tuple[Path, str] | None:
        variant = self.get_variant(asset_id, kind)
        if variant is None:
            return None
        path = Path(variant.local_path)
        if not path.exists():
            return None
        return path, variant.mime_type

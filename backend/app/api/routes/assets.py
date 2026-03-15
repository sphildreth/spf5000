from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.schemas.asset import AssetResponse
from app.services.asset_service import AssetService

router = APIRouter()
service = AssetService()


@router.get("", response_model=list[AssetResponse])
def list_assets(collection_id: str | None = None) -> list[AssetResponse]:
    return [AssetResponse.from_domain(asset) for asset in service.list_assets(collection_id=collection_id)]


@router.get("/{asset_id}", response_model=AssetResponse)
def get_asset(asset_id: str) -> AssetResponse:
    asset = service.get_asset(asset_id)
    if asset is None:
        raise HTTPException(status_code=404, detail="Asset not found")
    return AssetResponse.from_domain(asset)


@router.get("/{asset_id}/variants/{kind}")
def get_asset_variant(asset_id: str, kind: str) -> FileResponse:
    variant = service.get_variant_path(asset_id, kind)
    if variant is None:
        raise HTTPException(status_code=404, detail="Asset variant not found")
    path, media_type = variant
    return FileResponse(path=path, media_type=media_type, filename=path.name)

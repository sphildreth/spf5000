from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app.api.deps import require_admin
from app.schemas.asset import AssetResponse, AssetUploadResponse
from app.services.asset_service import AssetService

router = APIRouter()
service = AssetService()

_admin_dep = [Depends(require_admin)]


@router.get("", response_model=list[AssetResponse], dependencies=_admin_dep)
def list_assets(collection_id: str | None = None) -> list[AssetResponse]:
    return [AssetResponse.from_domain(asset) for asset in service.list_assets(collection_id=collection_id)]


@router.get("/{asset_id}", response_model=AssetResponse, dependencies=_admin_dep)
def get_asset(asset_id: str) -> AssetResponse:
    asset = service.get_asset(asset_id)
    if asset is None:
        raise HTTPException(status_code=404, detail="Asset not found")
    return AssetResponse.from_domain(asset)


@router.post("/upload", response_model=AssetUploadResponse, status_code=201, dependencies=_admin_dep)
def upload_assets(
    files: Annotated[list[UploadFile], File(description="One or more image files to import")],
    collection_id: Annotated[str | None, Form()] = None,
) -> AssetUploadResponse:
    try:
        summary = service.upload_files(files=files, collection_id=collection_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return AssetUploadResponse.from_domain(summary)


@router.get("/{asset_id}/variants/{kind}")  # intentionally public — served to the display client
def get_asset_variant(asset_id: str, kind: str) -> FileResponse:
    variant = service.get_variant_path(asset_id, kind)
    if variant is None:
        raise HTTPException(status_code=404, detail="Asset variant not found")
    path, media_type = variant
    return FileResponse(path=path, media_type=media_type, filename=path.name)

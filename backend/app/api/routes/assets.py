from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Response, UploadFile, status
from fastapi.responses import FileResponse

from app.api.deps import require_admin
from app.schemas.asset import AssetResponse, AssetUploadResponse, BulkRemoveRequest, BulkRemoveResponse
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


@router.post("/bulk-remove", response_model=BulkRemoveResponse, dependencies=_admin_dep)
def bulk_remove_assets(body: BulkRemoveRequest) -> BulkRemoveResponse:
    try:
        summary = service.bulk_remove_from_collection(
            collection_id=body.collection_id,
            asset_ids=body.asset_ids,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return BulkRemoveResponse(
        removed_count=summary.removed_count,
        deactivated_count=summary.deactivated_count,
        errors=summary.errors,
    )


@router.delete("/{asset_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=_admin_dep)
def remove_asset_from_collection(
    asset_id: str,
    collection_id: Annotated[str, Query(description="Collection membership to remove")],
) -> Response:
    try:
        service.remove_from_collection(asset_id=asset_id, collection_id=collection_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{asset_id}/variants/{kind}")  # intentionally public — served to the display client
def get_asset_variant(asset_id: str, kind: str) -> FileResponse:
    variant = service.get_variant_path(asset_id, kind)
    if variant is None:
        raise HTTPException(status_code=404, detail="Asset variant not found")
    path, media_type = variant
    return FileResponse(path=path, media_type=media_type, filename=path.name)

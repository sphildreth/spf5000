from fastapi import APIRouter, Depends, HTTPException

from app.schemas.source import SourceResponse, SourceUpdateRequest
from app.services.source_service import SourceService

router = APIRouter()


def get_source_service() -> SourceService:
    return SourceService()


@router.get("", response_model=list[SourceResponse])
def list_sources(
    svc: SourceService = Depends(get_source_service),
) -> list[SourceResponse]:
    return [SourceResponse.from_domain(source) for source in svc.list_sources()]


@router.put("/{source_id}", response_model=SourceResponse)
def update_source(
    source_id: str,
    request: SourceUpdateRequest,
    svc: SourceService = Depends(get_source_service),
) -> SourceResponse:
    updated = svc.update_source(
        source_id, request.name, request.import_path, request.enabled
    )
    if updated is None:
        raise HTTPException(status_code=404, detail="Source not found")
    return SourceResponse.from_domain(updated)

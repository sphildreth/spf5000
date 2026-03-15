from fastapi import APIRouter, Depends

from app.api.deps import require_admin
from app.schemas.display import DisplayConfigUpdateRequest, DisplayPlaylistResponse, DisplayProfileResponse
from app.services.display_service import DisplayService

router = APIRouter()
service = DisplayService()

_admin_dep = [Depends(require_admin)]


@router.get("/config", response_model=DisplayProfileResponse, dependencies=_admin_dep)
def get_display_config() -> DisplayProfileResponse:
    return DisplayProfileResponse.from_domain(service.get_config())


@router.put("/config", response_model=DisplayProfileResponse, dependencies=_admin_dep)
def update_display_config(request: DisplayConfigUpdateRequest) -> DisplayProfileResponse:
    updated = service.update_config(request.model_dump(exclude_unset=True))
    return DisplayProfileResponse.from_domain(updated)


@router.get("/playlist", response_model=DisplayPlaylistResponse)  # intentionally public
def get_display_playlist(collection_id: str | None = None) -> DisplayPlaylistResponse:
    return DisplayPlaylistResponse.from_domain(service.get_playlist(collection_id=collection_id))

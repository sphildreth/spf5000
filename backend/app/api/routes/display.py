from fastapi import APIRouter

from app.schemas.display import DisplayConfigUpdateRequest, DisplayPlaylistResponse, DisplayProfileResponse
from app.services.display_service import DisplayService

router = APIRouter()
service = DisplayService()


@router.get("/config", response_model=DisplayProfileResponse)
def get_display_config() -> DisplayProfileResponse:
    return DisplayProfileResponse.from_domain(service.get_config())


@router.put("/config", response_model=DisplayProfileResponse)
def update_display_config(request: DisplayConfigUpdateRequest) -> DisplayProfileResponse:
    updated = service.update_config(request.model_dump(exclude_unset=True))
    return DisplayProfileResponse.from_domain(updated)


@router.get("/playlist", response_model=DisplayPlaylistResponse)
def get_display_playlist(collection_id: str | None = None) -> DisplayPlaylistResponse:
    return DisplayPlaylistResponse.from_domain(service.get_playlist(collection_id=collection_id))

from fastapi import APIRouter

from app.models.settings import FrameSettings
from app.schemas.settings import SettingsResponse, SettingsUpdateRequest
from app.services.settings_service import SettingsService

router = APIRouter()
service = SettingsService()


@router.get("", response_model=SettingsResponse)
def get_settings() -> SettingsResponse:
    settings = service.get_settings()
    return SettingsResponse(**settings.__dict__)


@router.put("", response_model=SettingsResponse)
def update_settings(request: SettingsUpdateRequest) -> SettingsResponse:
    updated = service.update_settings(FrameSettings(**request.model_dump()))
    return SettingsResponse(**updated.__dict__)

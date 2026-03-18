from fastapi import APIRouter, Depends

from app.api.deps import require_admin
from app.schemas.display import (
    DisplayConfigUpdateRequest,
    DisplayPlaylistResponse,
    DisplayProfileResponse,
    PublicDisplayPlaylistResponse,
)
from app.schemas.weather import DisplayAlertsResponse, DisplayWeatherResponse
from app.services.display_service import DisplayService
from app.services.weather_service import WeatherService

router = APIRouter()
service = DisplayService()
weather_service = WeatherService()

_admin_dep = [Depends(require_admin)]


@router.get("/config", response_model=DisplayProfileResponse, dependencies=_admin_dep)
def get_display_config() -> DisplayProfileResponse:
    return DisplayProfileResponse.from_domain(service.get_config())


@router.put("/config", response_model=DisplayProfileResponse, dependencies=_admin_dep)
def update_display_config(
    request: DisplayConfigUpdateRequest,
) -> DisplayProfileResponse:
    updated = service.update_config(request.model_dump(exclude_unset=True))
    return DisplayProfileResponse.from_domain(updated)


@router.get(
    "/playlist", response_model=PublicDisplayPlaylistResponse
)  # intentionally public
def get_display_playlist(
    collection_id: str | None = None,
) -> PublicDisplayPlaylistResponse:
    return PublicDisplayPlaylistResponse.from_domain(
        service.get_playlist(collection_id=collection_id)
    )


@router.get("/weather", response_model=DisplayWeatherResponse)  # intentionally public
def get_display_weather() -> DisplayWeatherResponse:
    return DisplayWeatherResponse.model_validate(
        weather_service.get_display_weather_payload()
    )


@router.get("/alerts", response_model=DisplayAlertsResponse)  # intentionally public
def get_display_alerts() -> DisplayAlertsResponse:
    return DisplayAlertsResponse.model_validate(
        weather_service.get_display_alerts_payload()
    )

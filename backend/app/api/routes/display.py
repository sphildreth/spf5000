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
_admin_dep = [Depends(require_admin)]


def get_display_service() -> DisplayService:
    return DisplayService()


def get_weather_service() -> WeatherService:
    return WeatherService()


@router.get("/config", response_model=DisplayProfileResponse, dependencies=_admin_dep)
def get_display_config(
    svc: DisplayService = Depends(get_display_service),
) -> DisplayProfileResponse:
    return DisplayProfileResponse.from_domain(svc.get_config())


@router.put("/config", response_model=DisplayProfileResponse, dependencies=_admin_dep)
def update_display_config(
    request: DisplayConfigUpdateRequest,
    svc: DisplayService = Depends(get_display_service),
) -> DisplayProfileResponse:
    updated = svc.update_config(request.model_dump(exclude_unset=True))
    return DisplayProfileResponse.from_domain(updated)


@router.get(
    "/playlist", response_model=PublicDisplayPlaylistResponse
)  # intentionally public
def get_display_playlist(
    collection_id: str | None = None,
    svc: DisplayService = Depends(get_display_service),
) -> PublicDisplayPlaylistResponse:
    return PublicDisplayPlaylistResponse.from_domain(
        svc.get_playlist(collection_id=collection_id)
    )


@router.get("/weather", response_model=DisplayWeatherResponse)  # intentionally public
def get_display_weather(
    svc: WeatherService = Depends(get_weather_service),
) -> DisplayWeatherResponse:
    return DisplayWeatherResponse.model_validate(svc.get_display_weather_payload())


@router.get("/alerts", response_model=DisplayAlertsResponse)  # intentionally public
def get_display_alerts(
    svc: WeatherService = Depends(get_weather_service),
) -> DisplayAlertsResponse:
    return DisplayAlertsResponse.model_validate(svc.get_display_alerts_payload())

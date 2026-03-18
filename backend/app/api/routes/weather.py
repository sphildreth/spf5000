from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.schemas.weather import (
    WeatherAlertsResponse,
    WeatherSettingsResponse,
    WeatherSettingsUpdateRequest,
    WeatherStatusResponse,
)
from app.services.weather_service import WeatherService
from app.weather.errors import WeatherConfigurationError

router = APIRouter()


def get_weather_service() -> WeatherService:
    return WeatherService()


@router.get("/settings", response_model=WeatherSettingsResponse)
def get_weather_settings(
    svc: WeatherService = Depends(get_weather_service),
) -> WeatherSettingsResponse:
    return WeatherSettingsResponse.from_domain(svc.get_settings())


@router.put("/settings", response_model=WeatherSettingsResponse)
def update_weather_settings(
    request: WeatherSettingsUpdateRequest,
    svc: WeatherService = Depends(get_weather_service),
) -> WeatherSettingsResponse:
    updated = svc.update_settings(request.to_domain())
    return WeatherSettingsResponse.from_domain(updated)


@router.get("/status", response_model=WeatherStatusResponse)
def get_weather_status(
    svc: WeatherService = Depends(get_weather_service),
) -> WeatherStatusResponse:
    return WeatherStatusResponse.model_validate(svc.get_status_payload())


@router.get("/alerts", response_model=WeatherAlertsResponse)
def get_weather_alerts(
    svc: WeatherService = Depends(get_weather_service),
) -> WeatherAlertsResponse:
    return WeatherAlertsResponse.model_validate(svc.get_alerts_payload())


@router.post("/refresh", response_model=WeatherStatusResponse)
def refresh_weather(
    svc: WeatherService = Depends(get_weather_service),
) -> WeatherStatusResponse:
    try:
        payload = svc.refresh_all(trigger="manual")
    except WeatherConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    return WeatherStatusResponse.model_validate(payload)

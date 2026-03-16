from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from app.schemas.weather import (
    WeatherAlertsResponse,
    WeatherSettingsResponse,
    WeatherSettingsUpdateRequest,
    WeatherStatusResponse,
)
from app.services.weather_service import WeatherService
from app.weather.errors import WeatherConfigurationError

router = APIRouter()
service = WeatherService()


@router.get("/settings", response_model=WeatherSettingsResponse)
def get_weather_settings() -> WeatherSettingsResponse:
    return WeatherSettingsResponse.from_domain(service.get_settings())


@router.put("/settings", response_model=WeatherSettingsResponse)
def update_weather_settings(request: WeatherSettingsUpdateRequest) -> WeatherSettingsResponse:
    updated = service.update_settings(request.to_domain())
    return WeatherSettingsResponse.from_domain(updated)


@router.get("/status", response_model=WeatherStatusResponse)
def get_weather_status() -> WeatherStatusResponse:
    return WeatherStatusResponse.model_validate(service.get_status_payload())


@router.get("/alerts", response_model=WeatherAlertsResponse)
def get_weather_alerts() -> WeatherAlertsResponse:
    return WeatherAlertsResponse.model_validate(service.get_alerts_payload())


@router.post("/refresh", response_model=WeatherStatusResponse)
def refresh_weather() -> WeatherStatusResponse:
    try:
        payload = service.refresh_all(trigger="manual")
    except WeatherConfigurationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return WeatherStatusResponse.model_validate(payload)

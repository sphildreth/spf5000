from __future__ import annotations

from fastapi import FastAPI

from app.services.weather_service import WeatherService
from app.services.weather_sync_coordinator import WeatherSyncCoordinator


def start_background_coordinators(app: FastAPI) -> None:
    weather = getattr(app.state, "weather_sync_coordinator", None)
    if weather is None:
        weather = WeatherSyncCoordinator(service_factory=WeatherService)
        weather.start()
        app.state.weather_sync_coordinator = weather


def stop_background_coordinators(app: FastAPI) -> None:
    weather = getattr(app.state, "weather_sync_coordinator", None)
    if weather is not None:
        stop = getattr(weather, "stop", None)
        if callable(stop):
            stop()
        app.state.weather_sync_coordinator = None

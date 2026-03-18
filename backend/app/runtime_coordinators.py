from __future__ import annotations

from fastapi import FastAPI

from app.services.google_photos_service import GooglePhotosService
from app.services.google_photos_sync_coordinator import GooglePhotosSyncCoordinator
from app.services.weather_service import WeatherService
from app.services.weather_sync_coordinator import WeatherSyncCoordinator


def start_background_coordinators(app: FastAPI) -> None:
    google_photos = getattr(app.state, "google_photos_sync_coordinator", None)
    if google_photos is None:
        google_photos = GooglePhotosSyncCoordinator(service_factory=GooglePhotosService)
        google_photos.start()
        app.state.google_photos_sync_coordinator = google_photos

    weather = getattr(app.state, "weather_sync_coordinator", None)
    if weather is None:
        weather = WeatherSyncCoordinator(service_factory=WeatherService)
        weather.start()
        app.state.weather_sync_coordinator = weather


def stop_background_coordinators(app: FastAPI) -> None:
    google_photos = getattr(app.state, "google_photos_sync_coordinator", None)
    if google_photos is not None:
        stop = getattr(google_photos, "stop", None)
        if callable(stop):
            stop()
        app.state.google_photos_sync_coordinator = None

    weather = getattr(app.state, "weather_sync_coordinator", None)
    if weather is not None:
        stop = getattr(weather, "stop", None)
        if callable(stop):
            stop()
        app.state.weather_sync_coordinator = None

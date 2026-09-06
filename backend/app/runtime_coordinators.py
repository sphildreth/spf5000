from __future__ import annotations

from typing import Any

from fastapi import FastAPI

from app.services.auto_scan_coordinator import AutoScanCoordinator
from app.services.db_maintenance_coordinator import DatabaseMaintenanceCoordinator
from app.services.weather_service import WeatherService
from app.services.weather_sync_coordinator import WeatherSyncCoordinator


def start_background_coordinators(app: FastAPI) -> None:
    # Auto-scan coordinator (always starts, handles its own enabled/disabled state)
    auto_scan = getattr(app.state, "auto_scan_coordinator", None)
    if auto_scan is None:
        from app.services.import_service import ImportService
        from app.repositories.settings_repository import SettingsRepository
        from app.repositories.source_repository import SourceRepository
        from app.repositories.asset_repository import AssetRepository
        from app.services.asset_ingest_service import AssetIngestService

        settings_repo = SettingsRepository()
        source_repo = SourceRepository()
        asset_repo = AssetRepository()
        ingest_service = AssetIngestService(asset_repo=asset_repo, settings_repo=settings_repo)
        import_service = ImportService(
            settings_repo=settings_repo,
            source_repo=source_repo,
            asset_repo=asset_repo,
            ingest_service=ingest_service,
        )

        def trigger_scan_and_import() -> None:
            """Trigger an automatic scan and import of new files."""
            from app.core.config import settings

            source_id = settings_repo.get_setting("auto_scan_source_id", "default-local-files")
            collection_id = settings_repo.get_setting("selected_collection_id", "default-collection")

            scan_result = import_service.scan_directory(source_id, max_samples=100)

            if scan_result.discovered_count > 0:
                import_service.import_local_source(
                    source_id=source_id,
                    collection_id=collection_id,
                    max_samples=100,
                )

        auto_scan = AutoScanCoordinator(
            scan_trigger=trigger_scan_and_import,
            settings_repo=settings_repo,
        )
        auto_scan.start()
        app.state.auto_scan_coordinator = auto_scan

    # Database maintenance coordinator (WAL checkpoint)
    maintenance = getattr(app.state, "db_maintenance_coordinator", None)
    if maintenance is None:
        maintenance = DatabaseMaintenanceCoordinator()
        maintenance.start()
        app.state.db_maintenance_coordinator = maintenance

    # Weather coordinator
    weather = getattr(app.state, "weather_sync_coordinator", None)
    if weather is None:
        weather = WeatherSyncCoordinator(service_factory=WeatherService)
        weather.start()
        app.state.weather_sync_coordinator = weather


def stop_background_coordinators(app: FastAPI) -> None:
    # Stop database maintenance coordinator
    maintenance = getattr(app.state, "db_maintenance_coordinator", None)
    if maintenance is not None:
        stop = getattr(maintenance, "stop", None)
        if callable(stop):
            stop()
        app.state.db_maintenance_coordinator = None

    # Stop auto-scan coordinator
    auto_scan = getattr(app.state, "auto_scan_coordinator", None)
    if auto_scan is not None:
        stop = getattr(auto_scan, "stop", None)
        if callable(stop):
            stop()
        app.state.auto_scan_coordinator = None

    # Stop weather coordinator
    weather = getattr(app.state, "weather_sync_coordinator", None)
    if weather is not None:
        stop = getattr(weather, "stop", None)
        if callable(stop):
            stop()
        app.state.weather_sync_coordinator = None


def get_coordinator_status(app: FastAPI) -> dict[str, Any]:
    """Return status of all background coordinators for diagnostics."""
    auto_scan = getattr(app.state, "auto_scan_coordinator", None)
    weather = getattr(app.state, "weather_sync_coordinator", None)
    maintenance = getattr(app.state, "db_maintenance_coordinator", None)

    return {
        "auto_scan": auto_scan.get_status() if auto_scan else None,
        "weather": weather.get_status() if weather else None,
        "db_maintenance": maintenance.get_status() if maintenance else None,
    }

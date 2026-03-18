from __future__ import annotations

import shutil
from pathlib import Path

from fastapi import APIRouter, Depends

from app.api.deps import require_admin
from app.core.config import settings
from app.db.connection import is_decentdb_available
from app.schemas.system import HealthResponse
from app.services.system_service import SystemService

router = APIRouter()
system_service = SystemService()


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(
        ok=True,
        app=settings.app_name,
        version=settings.app_version,
        database_available=is_decentdb_available(),
    )


@router.get("/health/deep")
def deep_health() -> dict[str, object]:
    db_ok = is_decentdb_available()
    disk_usage: dict[str, object] = {}
    try:
        du = shutil.disk_usage(settings.data_dir)
        disk_usage = {
            "total_bytes": du.total,
            "used_bytes": du.used,
            "free_bytes": du.free,
            "percent_used": round((du.used / du.total) * 100, 1)
            if du.total > 0
            else 0.0,
        }
    except OSError:
        disk_usage = {"error": "Could not determine disk usage"}

    return {
        "ok": db_ok,
        "app": settings.app_name,
        "version": settings.app_version,
        "database": {
            "available": db_ok,
            "path": str(settings.database_path),
        },
        "disk_space": disk_usage,
        "cache_size_bytes": _dir_size(settings.cache_dir),
        "sync_status": {
            "google_photos": _get_sync_status(),
            "weather": _get_weather_status(),
        },
        "asset_count": _get_asset_count(),
    }


def _dir_size(path: Path) -> int:
    try:
        return sum(f.stat().st_size for f in path.rglob("*") if f.is_file())
    except OSError:
        return 0


def _get_asset_count() -> int:
    try:
        from app.repositories.asset_repository import AssetRepository

        return AssetRepository().count_assets()
    except Exception:
        return -1


def _get_sync_status() -> dict[str, object]:
    try:
        status = system_service.get_status()
        counts = status.get("counts")
        return dict(counts) if isinstance(counts, dict) else {}  # type: ignore[arg-type,return-value]
    except Exception:
        return {}


def _get_weather_status() -> dict[str, object]:
    try:
        from app.services.weather_service import WeatherService

        svc = WeatherService()
        state = svc.get_provider_state()
        return {
            "provider": state.provider_name if state else "unknown",
            "available": state.available if state else False,
            "last_refresh": state.last_successful_weather_refresh_at if state else None,
            "last_error": state.current_error
            if state and state.current_error
            else None,
        }
    except Exception:
        return {"error": "unavailable"}


@router.get("/status", dependencies=[Depends(require_admin)])
@router.get("/system/status", dependencies=[Depends(require_admin)])
def status() -> dict[str, object]:
    return system_service.get_status()

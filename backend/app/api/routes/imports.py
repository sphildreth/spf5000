from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import require_admin
from app.schemas.imports import ImportJobResponse, LocalImportRunRequest, LocalImportScanRequest, LocalImportScanResponse
from app.services.import_service import ImportService
from app.repositories.settings_repository import SettingsRepository

router = APIRouter()
service = ImportService()


@router.post("/local/scan", response_model=LocalImportScanResponse)
def scan_local_imports(request: LocalImportScanRequest) -> LocalImportScanResponse:
    try:
        job, scan_result = service.scan_local_source(request.source_id, max_samples=request.max_samples)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return LocalImportScanResponse(
        job=ImportJobResponse.from_domain(job),
        import_path=scan_result.import_path,
        discovered_count=scan_result.discovered_count,
        ignored_count=scan_result.ignored_count,
        sample_filenames=[item.filename for item in scan_result.discovered],
    )


@router.post("/local/run", response_model=ImportJobResponse)
def run_local_imports(request: LocalImportRunRequest) -> ImportJobResponse:
    try:
        job = service.import_local_source(
            source_id=request.source_id,
            collection_id=request.collection_id,
            max_samples=request.max_samples,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return ImportJobResponse.from_domain(job)


@router.get("/auto-scan/status")
def get_auto_scan_status(admin: dict = Depends(require_admin)) -> dict:
    """Get auto-scan configuration and status."""
    settings_repo = SettingsRepository()
    
    return {
        "auto_scan_enabled": settings_repo.get_setting("auto_scan_enabled", "0") == "1",
        "auto_scan_cron_schedule": settings_repo.get_setting("auto_scan_cron_schedule", ""),
        "auto_watch_enabled": settings_repo.get_setting("auto_watch_enabled", "0") == "1",
        "auto_watch_debounce_seconds": int(settings_repo.get_setting("auto_watch_debounce_seconds", "5")),
        "auto_scan_source_id": settings_repo.get_setting("auto_scan_source_id", "default-local-files"),
    }


@router.post("/auto-scan/configure")
def configure_auto_scan(request: dict, admin: dict = Depends(require_admin)) -> dict:
    """Configure auto-scan settings."""
    settings_repo = SettingsRepository()
    
    # Validate and update settings
    if "auto_scan_enabled" in request:
        settings_repo.set_setting("auto_scan_enabled", "1" if request["auto_scan_enabled"] else "0")
    
    if "auto_scan_cron_schedule" in request:
        # Validate cron expression
        cron_schedule = request["auto_scan_cron_schedule"].strip()
        if cron_schedule:
            try:
                from croniter import croniter
                croniter(cron_schedule)
            except Exception as exc:
                raise HTTPException(status_code=400, detail=f"Invalid cron expression: {exc}") from exc
        settings_repo.set_setting("auto_scan_cron_schedule", cron_schedule)
    
    if "auto_watch_enabled" in request:
        settings_repo.set_setting("auto_watch_enabled", "1" if request["auto_watch_enabled"] else "0")
    
    if "auto_watch_debounce_seconds" in request:
        debounce = max(1, min(60, int(request["auto_watch_debounce_seconds"])))
        settings_repo.set_setting("auto_watch_debounce_seconds", str(debounce))
    
    if "auto_scan_source_id" in request:
        settings_repo.set_setting("auto_scan_source_id", request["auto_scan_source_id"])
    
    # Reload coordinator settings
    from app.runtime_coordinators import get_coordinator_status
    # The coordinator will reload settings on next iteration
    
    return {
        "auto_scan_enabled": settings_repo.get_setting("auto_scan_enabled", "0") == "1",
        "auto_scan_cron_schedule": settings_repo.get_setting("auto_scan_cron_schedule", ""),
        "auto_watch_enabled": settings_repo.get_setting("auto_watch_enabled", "0") == "1",
        "auto_watch_debounce_seconds": int(settings_repo.get_setting("auto_watch_debounce_seconds", "5")),
        "auto_scan_source_id": settings_repo.get_setting("auto_scan_source_id", "default-local-files"),
    }

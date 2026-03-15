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


@router.get("/status", dependencies=[Depends(require_admin)])
@router.get("/system/status", dependencies=[Depends(require_admin)])
def status() -> dict[str, object]:
    return system_service.get_status()

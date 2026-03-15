from fastapi import APIRouter

from app.services.source_service import SourceService

router = APIRouter()
service = SourceService()


@router.get("")
def list_sources() -> list[dict[str, str]]:
    return service.list_sources()

from fastapi import APIRouter

from app.schemas.system import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(ok=True, app="SPF5000")

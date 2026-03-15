from fastapi import APIRouter

from app.api.routes import health, settings, sources

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(settings.router, prefix="/settings", tags=["settings"])
api_router.include_router(sources.router, prefix="/sources", tags=["sources"])

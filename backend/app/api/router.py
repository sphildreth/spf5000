from fastapi import APIRouter

from app.api.routes import assets, collections, display, health, imports, settings, sources

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(settings.router, prefix="/settings", tags=["settings"])
api_router.include_router(collections.router, prefix="/collections", tags=["collections"])
api_router.include_router(assets.router, prefix="/assets", tags=["assets"])
api_router.include_router(sources.router, prefix="/sources", tags=["sources"])
api_router.include_router(imports.router, prefix="/import", tags=["import"])
api_router.include_router(display.router, prefix="/display", tags=["display"])

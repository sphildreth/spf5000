from fastapi import APIRouter, Depends

from app.api.deps import require_admin
from app.api.routes import assets, auth, collections, display, health, imports, settings, sources

api_router = APIRouter()

# ── Public routes ──────────────────────────────────────────────────────────────
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router, tags=["auth"])

# ── Protected routes — require a valid admin session ───────────────────────────
_admin_dep = [Depends(require_admin)]

api_router.include_router(
    settings.router, prefix="/settings", tags=["settings"], dependencies=_admin_dep
)
api_router.include_router(
    collections.router, prefix="/collections", tags=["collections"], dependencies=_admin_dep
)
api_router.include_router(
    sources.router, prefix="/sources", tags=["sources"], dependencies=_admin_dep
)
api_router.include_router(
    imports.router, prefix="/import", tags=["import"], dependencies=_admin_dep
)

# Assets: list + detail are protected; variant fetch is public (served by display client).
api_router.include_router(assets.router, prefix="/assets", tags=["assets"])

# Display: playlist is public; config GET+PUT are protected.
api_router.include_router(display.router, prefix="/display", tags=["display"])

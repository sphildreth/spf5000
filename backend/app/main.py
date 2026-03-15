from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.router import api_router
from app.core.config import settings
from app.core.logging import configure_logging
from app.db.bootstrap import initialize_runtime


@asynccontextmanager
async def lifespan(_app: FastAPI):
    configure_logging()
    initialize_runtime()
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="SPF5000 API",
        version=settings.app_version,
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router, prefix="/api")
    app.mount("/fallback", StaticFiles(directory=settings.fallback_assets_dir, check_dir=False), name="fallback")

    static_dir = settings.frontend_dist_dir if settings.frontend_dist_dir.exists() else settings.legacy_frontend_dist_dir
    if static_dir.exists():
        app.mount("/", StaticFiles(directory=static_dir, html=True), name="frontend")

    return app


app = create_app()

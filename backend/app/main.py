from __future__ import annotations

import logging
import secrets
from contextlib import asynccontextmanager
from pathlib import PurePosixPath

from fastapi import FastAPI
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.api.router import api_router
from app.core.config import settings
from app.core.logging import configure_logging
from app.db.bootstrap import initialize_runtime
from app.runtime_coordinators import (
    start_background_coordinators,
    stop_background_coordinators,
)

_LOG = logging.getLogger(__name__)


class SPAStaticFiles(StaticFiles):
    """Serve built frontend assets and fall back to index.html for SPA routes."""

    async def get_response(self, path: str, scope):
        try:
            return await super().get_response(path, scope)
        except StarletteHTTPException as exc:
            if exc.status_code != 404:
                raise

            # Only treat extensionless paths as client-side routes. Missing asset files
            # should stay 404 so browser/network errors remain obvious.
            if PurePosixPath(path).suffix:
                raise

            return await super().get_response("index.html", scope)


def _resolve_session_secret() -> str:
    """Return the configured session secret, or generate an ephemeral one with a warning."""
    if settings.session_secret:
        return settings.session_secret
    secret = secrets.token_hex(32)
    _LOG.warning(
        "security.session_secret is not configured in spf5000.toml; "
        "using an ephemeral secret — admin sessions will be invalidated on every restart"
    )
    return secret


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    initialize_runtime()
    start_background_coordinators(app)
    try:
        yield
    finally:
        stop_background_coordinators(app)


def create_app() -> FastAPI:
    app = FastAPI(
        title="SPF5000 API",
        version=settings.app_version,
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )

    app.add_middleware(
        SessionMiddleware,
        secret_key=_resolve_session_secret(),
        session_cookie="spf5000_session",
        max_age=7 * 24 * 60 * 60,  # 7 days
        same_site="lax",
        https_only=settings.session_https_only,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router, prefix="/api")
    app.mount(
        "/fallback",
        StaticFiles(directory=settings.fallback_assets_dir, check_dir=False),
        name="fallback",
    )

    static_dir = (
        settings.frontend_dist_dir
        if settings.frontend_dist_dir.exists()
        else settings.legacy_frontend_dist_dir
    )
    if static_dir.exists():
        app.mount("/", SPAStaticFiles(directory=static_dir, html=True), name="frontend")

    return app


app = create_app()

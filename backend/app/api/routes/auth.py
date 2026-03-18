from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from app.api.rate_limit import check_rate_limit
from app.schemas.auth import (
    LoginRequest,
    SessionResponse,
    SessionUserResponse,
    SetupRequest,
)
from app.services.auth_service import AuthService

router = APIRouter()
_service = AuthService()


def _session_response(request: Request) -> SessionResponse:
    auth_available = _service.auth_available()
    bootstrapped = auth_available and _service.is_bootstrapped()
    if not auth_available:
        request.session.clear()
        return SessionResponse(
            auth_available=False,
            bootstrapped=False,
            authenticated=False,
            user=None,
        )

    admin_id = request.session.get("admin_id")
    if not admin_id:
        return SessionResponse(
            auth_available=True,
            bootstrapped=bootstrapped,
            authenticated=False,
            user=None,
        )

    user = _service.get_active_user(str(admin_id))
    if user is None:
        request.session.clear()
        return SessionResponse(
            auth_available=True,
            bootstrapped=bootstrapped,
            authenticated=False,
            user=None,
        )

    request.session["username"] = user.username
    return SessionResponse(
        auth_available=True,
        bootstrapped=bootstrapped,
        authenticated=True,
        user=SessionUserResponse(username=user.username),
    )


def _require_auth_available() -> None:
    if not _service.auth_available():
        raise HTTPException(
            status_code=503, detail="Admin authentication is unavailable"
        )


def _get_client_ip(request: Request) -> str:
    """Get the client IP address from the request."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


@router.post("/setup", response_model=SessionResponse)
def setup(request: Request, body: SetupRequest) -> SessionResponse:
    if not check_rate_limit(_get_client_ip(request), "5/minute"):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    _require_auth_available()
    if _service.is_bootstrapped():
        raise HTTPException(status_code=409, detail="System setup is already complete")

    user = _service.setup(body.username, body.password)
    request.session.clear()
    request.session["admin_id"] = user.id
    request.session["username"] = user.username
    return _session_response(request)


@router.get("/auth/session", response_model=SessionResponse)
def get_session(request: Request) -> SessionResponse:
    return _session_response(request)


@router.post("/auth/login", response_model=SessionResponse)
def login(request: Request, body: LoginRequest) -> SessionResponse:
    if not check_rate_limit(_get_client_ip(request), "10/minute"):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    _require_auth_available()
    if not _service.is_bootstrapped():
        raise HTTPException(
            status_code=409, detail="System setup must be completed before login"
        )

    user = _service.authenticate(body.username, body.password)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    request.session.clear()
    request.session["admin_id"] = user.id
    request.session["username"] = user.username
    return _session_response(request)


@router.post("/auth/logout", response_model=SessionResponse)
def logout(request: Request) -> SessionResponse:
    request.session.clear()
    return _session_response(request)

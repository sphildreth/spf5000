from __future__ import annotations

from fastapi import HTTPException, Request

from app.services.auth_service import AuthService

_auth_service = AuthService()


def require_admin(request: Request) -> dict[str, str]:
    """Raise 503 when auth is unavailable, otherwise require a valid admin session."""
    if not _auth_service.auth_available():
        raise HTTPException(status_code=503, detail="Admin authentication is unavailable")

    admin_id: str | None = request.session.get("admin_id")
    if not admin_id:
        raise HTTPException(status_code=401, detail="Authentication required")
    user = _auth_service.get_active_user(admin_id)
    if user is None:
        request.session.clear()
        raise HTTPException(status_code=401, detail="Authentication required")
    request.session["username"] = user.username
    return {"admin_id": admin_id, "username": user.username}

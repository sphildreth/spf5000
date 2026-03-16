from __future__ import annotations

from fastapi import APIRouter

from app.repositories.settings_repository import SettingsRepository
from app.schemas.theme import ThemesResponse
from app.services.theme_service import ThemeService

router = APIRouter()
_theme_service = ThemeService()
_settings_repo = SettingsRepository()


@router.get("", response_model=ThemesResponse)
def get_themes() -> ThemesResponse:
    """Return the active theme selection and all validated built-in theme definitions.

    This endpoint is public (no auth required) so the display client can fetch
    theme data without an admin session.
    """
    current = _settings_repo.get_settings()
    return _theme_service.get_themes_response(
        active_theme_id=current.theme_id,
        home_city_accent_style=current.home_city_accent_style,
    )

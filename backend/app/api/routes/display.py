from fastapi import APIRouter, Depends

from app.api.deps import require_admin
from app.schemas.display import (
    DisplayConfigUpdateRequest,
    DisplayPlaylistResponse,
    DisplayProfileResponse,
    DisplayRefreshResponse,
    PlaybackProgressRequest,
    PlaybackProgressResponse,
    PublicDisplayPlaylistResponse,
)
from app.schemas.weather import DisplayAlertsResponse, DisplayWeatherResponse
from app.services.display_service import DisplayService
from app.services.weather_service import WeatherService

router = APIRouter()
_admin_dep = [Depends(require_admin)]


def get_display_service() -> DisplayService:
    return DisplayService()


def get_weather_service() -> WeatherService:
    return WeatherService()


@router.get("/config", response_model=DisplayProfileResponse, dependencies=_admin_dep)
def get_display_config(
    svc: DisplayService = Depends(get_display_service),
) -> DisplayProfileResponse:
    return DisplayProfileResponse.from_domain(svc.get_config())


@router.put("/config", response_model=DisplayProfileResponse, dependencies=_admin_dep)
def update_display_config(
    request: DisplayConfigUpdateRequest,
    svc: DisplayService = Depends(get_display_service),
) -> DisplayProfileResponse:
    updated = svc.update_config(request.model_dump(exclude_unset=True))
    return DisplayProfileResponse.from_domain(updated)


@router.post("/refresh", response_model=DisplayRefreshResponse, dependencies=_admin_dep)
def refresh_display_cache(
    svc: DisplayService = Depends(get_display_service),
) -> DisplayRefreshResponse:
    invalidated_at = svc.refresh_playlist_cache()
    return DisplayRefreshResponse(refreshed=True, invalidated_at=invalidated_at)


@router.get(
    "/playlist", response_model=PublicDisplayPlaylistResponse
)  # intentionally public
def get_display_playlist(
    collection_id: str | None = None,
    svc: DisplayService = Depends(get_display_service),
) -> PublicDisplayPlaylistResponse:
    return PublicDisplayPlaylistResponse.from_domain(
        svc.get_playlist(collection_id=collection_id)
    )


@router.post(
    "/playlist/progress", response_model=PlaybackProgressResponse
)  # intentionally public, matches the public playlist
def report_display_playlist_progress(
    request: PlaybackProgressRequest,
    svc: DisplayService = Depends(get_display_service),
) -> PlaybackProgressResponse:
    """Advance the server-owned playback cursor past a photograph the display just showed.

    Only accepts identifiers that belong to the current cycle, so it cannot grow state.
    """
    cycle = svc.report_playback_position(
        asset_id=request.asset_id, collection_id=request.collection_id
    )
    if cycle is None:
        return PlaybackProgressResponse(
            accepted=False, playback_position=0, playback_cycle_id=""
        )
    return PlaybackProgressResponse(
        accepted=True,
        playback_position=cycle.position,
        playback_cycle_id=cycle.cycle_id,
    )


@router.get("/new-assets/count")
def get_new_assets_count(
    since: str,
    collection_id: str | None = None,
    svc: DisplayService = Depends(get_display_service),
) -> dict:
    """Check if there are new assets imported since the given timestamp."""
    count = svc.count_new_assets_since(since, collection_id)
    return {"new_assets_count": count, "since": since}


@router.get("/weather", response_model=DisplayWeatherResponse)  # intentionally public
def get_display_weather(
    svc: WeatherService = Depends(get_weather_service),
) -> DisplayWeatherResponse:
    return DisplayWeatherResponse.model_validate(svc.get_display_weather_payload())


@router.get("/alerts", response_model=DisplayAlertsResponse)  # intentionally public
def get_display_alerts(
    svc: WeatherService = Depends(get_weather_service),
) -> DisplayAlertsResponse:
    return DisplayAlertsResponse.model_validate(svc.get_display_alerts_payload())

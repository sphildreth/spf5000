from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from app.models.display import DisplayPlaylist, DisplayProfile, PlaylistItem
from app.schemas.settings import SleepScheduleResponse
from app.services.background_service import VALID_BACKGROUND_FILL_MODES


class DisplayProfileResponse(BaseModel):
    id: str
    name: str
    selected_collection_id: str | None
    slideshow_interval_seconds: int
    transition_mode: str
    transition_duration_ms: int
    fit_mode: str
    shuffle_enabled: bool
    shuffle_bag_enabled: bool
    idle_message: str
    refresh_interval_seconds: int
    is_default: bool
    created_at: str
    updated_at: str
    background_fill_mode: str

    @classmethod
    def from_domain(cls, profile: DisplayProfile) -> "DisplayProfileResponse":
        return cls(
            id=profile.id,
            name=profile.name,
            selected_collection_id=profile.selected_collection_id,
            slideshow_interval_seconds=profile.slideshow_interval_seconds,
            transition_mode=profile.transition_mode,
            transition_duration_ms=profile.transition_duration_ms,
            fit_mode=profile.fit_mode,
            shuffle_enabled=profile.shuffle_enabled,
            shuffle_bag_enabled=profile.shuffle_bag_enabled,
            idle_message=profile.idle_message,
            refresh_interval_seconds=profile.refresh_interval_seconds,
            is_default=profile.is_default,
            created_at=profile.created_at,
            updated_at=profile.updated_at,
            background_fill_mode=profile.background_fill_mode,
        )


class DisplayConfigUpdateRequest(BaseModel):
    name: str | None = None
    selected_collection_id: str | None = None
    slideshow_interval_seconds: int | None = Field(default=None, ge=1, le=3600)
    transition_mode: str | None = None
    transition_duration_ms: int | None = Field(default=None, ge=0, le=30000)
    fit_mode: str | None = None
    shuffle_enabled: bool | None = None
    shuffle_bag_enabled: bool | None = None
    idle_message: str | None = None
    refresh_interval_seconds: int | None = Field(default=None, ge=15, le=86400)
    background_fill_mode: str | None = None

    @field_validator("background_fill_mode")
    @classmethod
    def validate_background_fill_mode(cls, value: str | None) -> str | None:
        if value is None:
            return value
        if value not in VALID_BACKGROUND_FILL_MODES:
            raise ValueError(
                f"background_fill_mode must be one of {sorted(VALID_BACKGROUND_FILL_MODES)!r}, got {value!r}"
            )
        return value


class PlaylistItemBackgroundResponse(BaseModel):
    """Subdued background fill colours derived from the display variant."""

    ready: bool
    dominant_color: str
    gradient_colors: list[str]


class PlaylistItemResponse(BaseModel):
    asset_id: str
    filename: str
    display_url: str
    thumbnail_url: str
    width: int
    height: int
    checksum_sha256: str
    mime_type: str
    background: PlaylistItemBackgroundResponse | None = None

    @classmethod
    def from_domain(cls, item: PlaylistItem) -> "PlaylistItemResponse":
        bg: PlaylistItemBackgroundResponse | None = None
        if item.background is not None:
            bg = PlaylistItemBackgroundResponse(
                ready=item.background.ready,
                dominant_color=item.background.dominant_color,
                gradient_colors=item.background.gradient_colors,
            )
        return cls(
            asset_id=item.asset_id,
            filename=item.filename,
            display_url=item.display_url,
            thumbnail_url=item.thumbnail_url,
            width=item.width,
            height=item.height,
            checksum_sha256=item.checksum_sha256,
            mime_type=item.mime_type,
            background=bg,
        )


class DisplayPlaylistResponse(BaseModel):
    collection_id: str | None
    collection_name: str | None
    shuffle_enabled: bool
    playlist_revision: str
    background_fill_mode: str
    sleep_schedule: SleepScheduleResponse
    profile: DisplayProfileResponse
    items: list[PlaylistItemResponse]

    @classmethod
    def from_domain(cls, playlist: DisplayPlaylist) -> "DisplayPlaylistResponse":
        return cls(
            collection_id=playlist.collection_id,
            collection_name=playlist.collection_name,
            shuffle_enabled=playlist.shuffle_enabled,
            playlist_revision=playlist.playlist_revision,
            background_fill_mode=playlist.background_fill_mode,
            sleep_schedule=SleepScheduleResponse.from_domain(playlist.sleep_schedule),
            profile=DisplayProfileResponse.from_domain(playlist.profile),
            items=[PlaylistItemResponse.from_domain(item) for item in playlist.items],
        )

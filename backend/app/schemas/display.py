from __future__ import annotations

from dataclasses import asdict

from pydantic import BaseModel, Field

from app.models.display import DisplayPlaylist, DisplayProfile, PlaylistItem


class DisplayProfileResponse(BaseModel):
    id: str
    name: str
    selected_collection_id: str | None
    slideshow_interval_seconds: int
    transition_mode: str
    transition_duration_ms: int
    fit_mode: str
    shuffle_enabled: bool
    idle_message: str
    refresh_interval_seconds: int
    is_default: bool
    created_at: str
    updated_at: str

    @classmethod
    def from_domain(cls, profile: DisplayProfile) -> "DisplayProfileResponse":
        return cls(**asdict(profile))


class DisplayConfigUpdateRequest(BaseModel):
    name: str | None = None
    selected_collection_id: str | None = None
    slideshow_interval_seconds: int | None = Field(default=None, ge=1, le=3600)
    transition_mode: str | None = None
    transition_duration_ms: int | None = Field(default=None, ge=0, le=30000)
    fit_mode: str | None = None
    shuffle_enabled: bool | None = None
    idle_message: str | None = None
    refresh_interval_seconds: int | None = Field(default=None, ge=15, le=86400)


class PlaylistItemResponse(BaseModel):
    asset_id: str
    filename: str
    display_url: str
    thumbnail_url: str
    width: int
    height: int
    checksum_sha256: str
    mime_type: str

    @classmethod
    def from_domain(cls, item: PlaylistItem) -> "PlaylistItemResponse":
        return cls(**asdict(item))


class DisplayPlaylistResponse(BaseModel):
    collection_id: str | None
    collection_name: str | None
    shuffle_enabled: bool
    playlist_revision: str
    profile: DisplayProfileResponse
    items: list[PlaylistItemResponse]

    @classmethod
    def from_domain(cls, playlist: DisplayPlaylist) -> "DisplayPlaylistResponse":
        return cls(
            collection_id=playlist.collection_id,
            collection_name=playlist.collection_name,
            shuffle_enabled=playlist.shuffle_enabled,
            playlist_revision=playlist.playlist_revision,
            profile=DisplayProfileResponse.from_domain(playlist.profile),
            items=[PlaylistItemResponse.from_domain(item) for item in playlist.items],
        )

from __future__ import annotations

from dataclasses import dataclass, field

from app.models.asset import AssetBackground
from app.models.sleep_schedule import SleepSchedule


@dataclass(slots=True)
class DisplayProfile:
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
    background_fill_mode: str = "black"


@dataclass(slots=True)
class PlaylistItem:
    asset_id: str
    filename: str
    display_url: str
    thumbnail_url: str
    width: int
    height: int
    checksum_sha256: str
    mime_type: str
    background: AssetBackground | None = None


@dataclass(slots=True)
class DisplayPlaylist:
    profile: DisplayProfile
    collection_id: str | None
    collection_name: str | None
    shuffle_enabled: bool
    playlist_revision: str
    background_fill_mode: str = "black"
    sleep_schedule: SleepSchedule = field(default_factory=SleepSchedule)
    items: list[PlaylistItem] = field(default_factory=list)

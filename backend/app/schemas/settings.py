from __future__ import annotations

from dataclasses import asdict

from pydantic import BaseModel, Field

from app.models.settings import FrameSettings


class SettingsResponse(BaseModel):
    frame_name: str
    display_variant_width: int
    display_variant_height: int
    thumbnail_max_size: int
    slideshow_interval_seconds: int
    transition_mode: str
    transition_duration_ms: int
    fit_mode: str
    shuffle_enabled: bool
    selected_collection_id: str
    active_display_profile_id: str

    @classmethod
    def from_domain(cls, value: FrameSettings) -> "SettingsResponse":
        return cls(**asdict(value))


class SettingsUpdateRequest(BaseModel):
    frame_name: str = Field(min_length=1, max_length=120)
    display_variant_width: int = Field(ge=320, le=8192)
    display_variant_height: int = Field(ge=240, le=8192)
    thumbnail_max_size: int = Field(ge=64, le=4096)
    slideshow_interval_seconds: int = Field(ge=1, le=3600)
    transition_mode: str
    transition_duration_ms: int = Field(ge=0, le=30000)
    fit_mode: str
    shuffle_enabled: bool
    selected_collection_id: str
    active_display_profile_id: str

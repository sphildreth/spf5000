from __future__ import annotations

from dataclasses import dataclass

from app.db.bootstrap import DEFAULT_COLLECTION_ID, DEFAULT_DISPLAY_PROFILE_ID


@dataclass(slots=True)
class FrameSettings:
    frame_name: str = "SPF5000"
    display_variant_width: int = 1920
    display_variant_height: int = 1080
    thumbnail_max_size: int = 400
    slideshow_interval_seconds: int = 30
    transition_mode: str = "slide"
    transition_duration_ms: int = 700
    fit_mode: str = "contain"
    shuffle_enabled: bool = True
    shuffle_bag_enabled: bool = False
    selected_collection_id: str = DEFAULT_COLLECTION_ID
    active_display_profile_id: str = DEFAULT_DISPLAY_PROFILE_ID
    background_fill_mode: str = "black"

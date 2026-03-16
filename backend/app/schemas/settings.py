from __future__ import annotations

import re
from dataclasses import asdict

from pydantic import BaseModel, Field, field_validator, model_validator

from app.models.settings import FrameSettings
from app.models.sleep_schedule import (
    SleepSchedule,
    normalize_display_timezone,
    normalize_hhmm,
    normalize_sleep_schedule,
)
from app.models.time_reference import SleepScheduleTimeReference
from app.services.background_service import VALID_BACKGROUND_FILL_MODES

_HHMM_RE = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)$")


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
    shuffle_bag_enabled: bool
    selected_collection_id: str
    active_display_profile_id: str
    background_fill_mode: str
    theme_id: str
    home_city_accent_style: str

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
    shuffle_bag_enabled: bool = False
    selected_collection_id: str
    active_display_profile_id: str
    background_fill_mode: str = "black"
    theme_id: str = "default-dark"
    home_city_accent_style: str = "default"

    @field_validator("background_fill_mode")
    @classmethod
    def validate_background_fill_mode(cls, v: str) -> str:
        if v not in VALID_BACKGROUND_FILL_MODES:
            raise ValueError(
                f"background_fill_mode must be one of {sorted(VALID_BACKGROUND_FILL_MODES)!r}, got {v!r}"
            )
        return v


def _validate_hhmm(value: str, field_name: str) -> str:
    if not _HHMM_RE.match(value):
        raise ValueError(
            f"{field_name} must be a valid 24-hour time in HH:MM format (e.g. '22:00'), got {value!r}"
        )
    return normalize_hhmm(value)


class SleepScheduleResponse(BaseModel):
    sleep_schedule_enabled: bool
    sleep_start_local_time: str
    sleep_end_local_time: str
    display_timezone: str | None = None

    @classmethod
    def from_domain(cls, value: SleepSchedule) -> "SleepScheduleResponse":
        return cls(
            sleep_schedule_enabled=value.sleep_schedule_enabled,
            sleep_start_local_time=value.sleep_start_local_time,
            sleep_end_local_time=value.sleep_end_local_time,
            display_timezone=value.display_timezone,
        )


class SleepScheduleUpdateRequest(BaseModel):
    sleep_schedule_enabled: bool
    sleep_start_local_time: str
    sleep_end_local_time: str
    display_timezone: str | None = None

    @field_validator("sleep_start_local_time")
    @classmethod
    def validate_start(cls, v: str) -> str:
        return _validate_hhmm(v, "sleep_start_local_time")

    @field_validator("sleep_end_local_time")
    @classmethod
    def validate_end(cls, v: str) -> str:
        return _validate_hhmm(v, "sleep_end_local_time")

    @field_validator("display_timezone")
    @classmethod
    def validate_display_timezone(cls, v: str | None) -> str | None:
        return normalize_display_timezone(v)

    @model_validator(mode="after")
    def reject_equal_start_end_when_enabled(self) -> "SleepScheduleUpdateRequest":
        try:
            normalized = normalize_sleep_schedule(
                SleepSchedule(
                    sleep_schedule_enabled=self.sleep_schedule_enabled,
                    sleep_start_local_time=self.sleep_start_local_time,
                    sleep_end_local_time=self.sleep_end_local_time,
                    display_timezone=self.display_timezone,
                )
            )
        except ValueError as exc:
            if "display_timezone" in str(exc):
                raise ValueError(str(exc)) from exc
            raise ValueError(
                "sleep_start_local_time and sleep_end_local_time must differ when the schedule is enabled; "
                f"both are currently {self.sleep_start_local_time!r}"
            ) from exc
        self.sleep_start_local_time = normalized.sleep_start_local_time
        self.sleep_end_local_time = normalized.sleep_end_local_time
        self.display_timezone = normalized.display_timezone
        return self


class SleepScheduleTimeReferenceResponse(BaseModel):
    current_server_utc_timestamp: str
    pi_local_timezone: str
    configured_display_timezone: str | None
    effective_display_timezone: str
    available_timezones: list[str]

    @classmethod
    def from_domain(cls, value: SleepScheduleTimeReference) -> "SleepScheduleTimeReferenceResponse":
        return cls(**asdict(value))

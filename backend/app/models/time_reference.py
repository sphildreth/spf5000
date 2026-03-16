from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class SleepScheduleTimeReference:
    current_server_utc_timestamp: str
    pi_local_timezone: str
    configured_display_timezone: str | None
    effective_display_timezone: str
    available_timezones: list[str]

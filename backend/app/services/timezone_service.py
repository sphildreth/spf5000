from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from zoneinfo import ZoneInfo, available_timezones

from app.models.sleep_schedule import SleepSchedule
from app.models.time_reference import SleepScheduleTimeReference

AVAILABLE_TIMEZONES = sorted(available_timezones()) or ["UTC"]
_AVAILABLE_TIMEZONE_SET = frozenset(AVAILABLE_TIMEZONES)
_ETC_TIMEZONE_PATH = Path("/etc/timezone")
_LOCALTIME_PATH = Path("/etc/localtime")
_ZONEINFO_ROOT = Path("/usr/share/zoneinfo")


def get_pi_local_timezone_name(now: datetime | None = None) -> str:
    for candidate in (
        _timezone_from_zoneinfo(now),
        _timezone_from_etc_timezone(),
        _timezone_from_localtime_symlink(),
    ):
        if candidate and candidate in _AVAILABLE_TIMEZONE_SET:
            return candidate
    return "UTC"


def _timezone_from_zoneinfo(now: datetime | None = None) -> str | None:
    local_tzinfo = (now or datetime.now(UTC)).astimezone().tzinfo
    if isinstance(local_tzinfo, ZoneInfo):
        return local_tzinfo.key
    return None


def _timezone_from_etc_timezone() -> str | None:
    if not _ETC_TIMEZONE_PATH.is_file():
        return None
    candidate = _ETC_TIMEZONE_PATH.read_text(encoding="utf-8").strip()
    return candidate or None


def _timezone_from_localtime_symlink() -> str | None:
    if not _LOCALTIME_PATH.exists() or not _LOCALTIME_PATH.is_symlink():
        return None
    resolved = _LOCALTIME_PATH.resolve()
    try:
        candidate = resolved.relative_to(_ZONEINFO_ROOT).as_posix()
    except ValueError:
        return None
    return candidate or None


def get_effective_display_timezone(schedule: SleepSchedule, pi_local_timezone: str) -> str:
    return schedule.display_timezone or pi_local_timezone


def build_sleep_schedule_time_reference(
    schedule: SleepSchedule,
    now_utc: datetime | None = None,
) -> SleepScheduleTimeReference:
    current_utc = (now_utc or datetime.now(UTC)).astimezone(UTC)
    pi_local_timezone = get_pi_local_timezone_name(current_utc)
    configured_display_timezone = schedule.display_timezone
    return SleepScheduleTimeReference(
        current_server_utc_timestamp=current_utc.isoformat(),
        pi_local_timezone=pi_local_timezone,
        configured_display_timezone=configured_display_timezone,
        effective_display_timezone=get_effective_display_timezone(schedule, pi_local_timezone),
        available_timezones=AVAILABLE_TIMEZONES,
    )

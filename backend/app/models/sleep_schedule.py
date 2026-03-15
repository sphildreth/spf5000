from __future__ import annotations

from dataclasses import dataclass, replace


@dataclass(slots=True)
class SleepSchedule:
    sleep_schedule_enabled: bool = False
    sleep_start_local_time: str = "22:00"
    sleep_end_local_time: str = "08:00"


def parse_hhmm(time_str: str) -> tuple[int, int]:
    """Parse an 'HH:MM' string to ``(hour, minute)``.  Raises :exc:`ValueError` on bad input.

    The format is strict: both hour and minute must be exactly two decimal digits, separated
    by a colon (e.g. ``'09:05'``, not ``'9:5'``).
    """
    parts = time_str.split(":")
    if len(parts) != 2 or len(parts[0]) != 2 or len(parts[1]) != 2:
        raise ValueError(
            f"Invalid HH:MM time: {time_str!r} — expected format is HH:MM with two-digit hour and minute"
        )
    try:
        hour, minute = int(parts[0]), int(parts[1])
    except ValueError:
        raise ValueError(f"Invalid HH:MM time: {time_str!r} — hour and minute must be integers")
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        raise ValueError(
            f"Time out of range: {time_str!r} — hour must be 0–23 and minute must be 0–59"
        )
    return hour, minute


def _to_minutes(hour: int, minute: int) -> int:
    return hour * 60 + minute


def normalize_hhmm(time_str: str) -> str:
    hour, minute = parse_hhmm(time_str)
    return f"{hour:02d}:{minute:02d}"


def normalize_sleep_schedule(schedule: SleepSchedule) -> SleepSchedule:
    normalized = replace(
        schedule,
        sleep_start_local_time=normalize_hhmm(schedule.sleep_start_local_time),
        sleep_end_local_time=normalize_hhmm(schedule.sleep_end_local_time),
    )
    if (
        normalized.sleep_schedule_enabled
        and normalized.sleep_start_local_time == normalized.sleep_end_local_time
    ):
        raise ValueError(
            "sleep_start_local_time and sleep_end_local_time must differ when the schedule is enabled"
        )
    return normalized


def is_in_sleep_window(current_hhmm: str, schedule: SleepSchedule) -> bool:
    """Return ``True`` when *current_hhmm* falls inside the configured sleep window.

    Rules
    -----
    * If the schedule is disabled, always returns ``False``.
    * Boundary times (exactly *start* or exactly *end*) are considered **inside** the window.
    * Overnight windows (start > end, e.g. 22:00–08:00) are handled correctly by wrapping
      around midnight.
    * A normal (same-day) window (start < end, e.g. 14:00–16:00) is handled as a simple
      inclusive range.
    * start == end is undefined — callers should prevent this via validation before reaching
      this function.

    Parameters
    ----------
    current_hhmm:
        The device-local time as an ``'HH:MM'`` string.
    schedule:
        The :class:`SleepSchedule` to evaluate against.
    """
    normalized = normalize_sleep_schedule(schedule)

    if not normalized.sleep_schedule_enabled:
        return False

    start_h, start_m = parse_hhmm(normalized.sleep_start_local_time)
    end_h, end_m = parse_hhmm(normalized.sleep_end_local_time)
    cur_h, cur_m = parse_hhmm(current_hhmm)

    start = _to_minutes(start_h, start_m)
    end = _to_minutes(end_h, end_m)
    cur = _to_minutes(cur_h, cur_m)

    if start < end:
        # Same-day window, e.g. 14:00–16:00
        return start <= cur <= end
    else:
        # Overnight window, e.g. 22:00–08:00 (crosses midnight)
        return cur >= start or cur <= end

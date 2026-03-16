from __future__ import annotations

from datetime import UTC, datetime

from app.models.weather import ResolvedWeatherAlert, WeatherAlert, WeatherSettings

_FULLSCREEN_REPEAT_EVENTS = {
    "tornado warning",
    "flash flood warning",
    "civil danger warning",
    "evacuation immediate",
    "shelter in place warning",
}
_FULLSCREEN_EVENTS = {
    "severe thunderstorm warning",
    "ice storm warning",
    "blizzard warning",
    "dust storm warning",
    "extreme wind warning",
}
_BANNER_EVENTS = {
    "tornado watch",
    "severe thunderstorm watch",
    "flood advisory",
    "winter weather advisory",
    "dense fog advisory",
    "heat advisory",
    "wind advisory",
}
_BADGE_EVENTS = {
    "flood watch",
    "freeze watch",
    "frost advisory",
    "special weather statement",
    "hazardous weather outlook",
}
_EVENT_PRIORITY = {
    "tornado warning": 100,
    "flash flood warning": 95,
    "civil danger warning": 94,
    "evacuation immediate": 93,
    "shelter in place warning": 92,
    "severe thunderstorm warning": 85,
    "ice storm warning": 84,
    "blizzard warning": 83,
    "dust storm warning": 82,
    "extreme wind warning": 81,
    "tornado watch": 70,
    "severe thunderstorm watch": 69,
    "flood advisory": 60,
    "winter weather advisory": 59,
    "dense fog advisory": 58,
    "heat advisory": 57,
    "wind advisory": 56,
    "flood watch": 45,
    "freeze watch": 44,
    "frost advisory": 43,
    "special weather statement": 42,
    "hazardous weather outlook": 41,
}
_SEVERITY_RANK = {
    "unknown": 0,
    "minor": 1,
    "moderate": 2,
    "severe": 3,
    "extreme": 4,
}
_ESCALATION_RANK = {
    "ignore": 0,
    "badge": 1,
    "banner": 2,
    "fullscreen": 3,
    "fullscreen_repeat": 4,
}


def resolve_default_escalation_mode(event: str, status: str | None = None) -> str:
    normalized_event = (event or "").strip().lower()
    normalized_status = (status or "").strip().lower()
    if normalized_status and normalized_status != "actual":
        return "ignore"
    if "test" in normalized_event:
        return "ignore"
    if normalized_event in _FULLSCREEN_REPEAT_EVENTS:
        return "fullscreen_repeat"
    if normalized_event in _FULLSCREEN_EVENTS:
        return "fullscreen"
    if normalized_event in _BANNER_EVENTS:
        return "banner"
    if normalized_event in _BADGE_EVENTS:
        return "badge"
    if normalized_event.endswith(" warning"):
        return "fullscreen"
    if normalized_event.endswith(" watch"):
        return "banner"
    if normalized_event.endswith(" advisory"):
        return "banner"
    if normalized_event.endswith(" statement") or normalized_event.endswith(" outlook"):
        return "badge"
    return "badge"


def event_priority(event: str) -> int:
    return _EVENT_PRIORITY.get((event or "").strip().lower(), 10)


def severity_rank(severity: str) -> int:
    return _SEVERITY_RANK.get((severity or "").strip().lower(), 0)


def escalation_rank(mode: str) -> int:
    return _ESCALATION_RANK.get((mode or "").strip().lower(), 0)


def resolve_effective_escalation_mode(alert: WeatherAlert, settings: WeatherSettings) -> str:
    if not settings.weather_alerts_enabled:
        return "ignore"
    if severity_rank(alert.severity) < severity_rank(settings.weather_alert_minimum_severity):
        return "ignore"
    mode = alert.escalation_mode
    if mode in {"fullscreen", "fullscreen_repeat"} and not settings.weather_alert_fullscreen_enabled:
        mode = "banner"
    if mode == "fullscreen_repeat" and not settings.weather_alert_repeat_enabled:
        mode = "fullscreen"
    return mode


def resolve_alert(alert: WeatherAlert, settings: WeatherSettings) -> ResolvedWeatherAlert | None:
    effective_mode = resolve_effective_escalation_mode(alert, settings)
    if effective_mode == "ignore":
        return None
    effective_display_priority = (
        escalation_rank(effective_mode) * 1_000_000
        + severity_rank(alert.severity) * 10_000
        + event_priority(alert.event) * 100
        + max(_issued_timestamp_rank(alert), 0)
    )
    return ResolvedWeatherAlert(
        alert=alert,
        effective_escalation_mode=effective_mode,
        effective_display_priority=effective_display_priority,
    )


def resolve_active_alerts(alerts: list[WeatherAlert], settings: WeatherSettings) -> list[ResolvedWeatherAlert]:
    resolved = [item for item in (resolve_alert(alert, settings) for alert in alerts) if item is not None]
    return sorted(resolved, key=_sort_key, reverse=True)


def select_dominant_alert(alerts: list[WeatherAlert], settings: WeatherSettings) -> ResolvedWeatherAlert | None:
    resolved = resolve_active_alerts(alerts, settings)
    return resolved[0] if resolved else None


def _sort_key(value: ResolvedWeatherAlert) -> tuple[int, int, int, int]:
    return (
        escalation_rank(value.effective_escalation_mode),
        severity_rank(value.alert.severity),
        event_priority(value.alert.event),
        _issued_timestamp_rank(value.alert),
    )


def _issued_timestamp_rank(alert: WeatherAlert) -> int:
    for candidate in (alert.issued_at, alert.effective_at, alert.updated_at):
        if not candidate:
            continue
        try:
            timestamp = datetime.fromisoformat(candidate.replace("Z", "+00:00"))
        except ValueError:
            continue
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=UTC)
        return int(timestamp.timestamp())
    return 0

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

AlertEscalationMode = Literal["ignore", "badge", "banner", "fullscreen", "fullscreen_repeat"]
WeatherUnits = Literal["f", "c"]
WeatherWidgetPosition = Literal["top-left", "top-right", "bottom-left", "bottom-right"]
AlertSeverity = Literal["unknown", "minor", "moderate", "severe", "extreme"]

_VALID_UNITS = {"f", "c"}
_VALID_POSITIONS = {"top-left", "top-right", "bottom-left", "bottom-right"}
_VALID_SEVERITIES = {"unknown", "minor", "moderate", "severe", "extreme"}


@dataclass(slots=True)
class WeatherLocation:
    label: str = ""
    latitude: float | None = None
    longitude: float | None = None

    @property
    def is_configured(self) -> bool:
        return self.latitude is not None and self.longitude is not None


@dataclass(slots=True)
class WeatherSettings:
    weather_enabled: bool = False
    weather_provider: str = "nws"
    weather_location: WeatherLocation = field(default_factory=WeatherLocation)
    weather_units: WeatherUnits = "f"
    weather_position: WeatherWidgetPosition = "top-right"
    weather_refresh_minutes: int = 15
    weather_show_precipitation: bool = True
    weather_show_humidity: bool = True
    weather_show_wind: bool = True
    weather_alerts_enabled: bool = True
    weather_alert_fullscreen_enabled: bool = True
    weather_alert_minimum_severity: AlertSeverity = "minor"
    weather_alert_repeat_enabled: bool = True
    weather_alert_repeat_interval_minutes: int = 5
    weather_alert_repeat_display_seconds: int = 20


@dataclass(slots=True)
class WeatherCurrentConditions:
    provider_name: str
    provider_display_name: str
    location_key: str
    location_label: str
    condition: str
    icon_token: str
    temperature_c: float | None
    humidity_percent: int | None
    wind_speed_mph: float | None
    wind_direction: str | None
    precipitation_probability_percent: int | None
    observed_at: str | None
    fetched_at: str
    attribution: str = "National Weather Service"
    is_stale: bool = False


@dataclass(slots=True)
class WeatherAlert:
    id: str
    provider_name: str
    provider_display_name: str
    location_key: str
    source_alert_id: str
    event: str
    severity: AlertSeverity
    certainty: str
    urgency: str
    headline: str
    description: str
    instruction: str
    area: str
    status: str
    issued_at: str | None
    effective_at: str | None
    expires_at: str | None
    ends_at: str | None
    attribution: str
    escalation_mode: AlertEscalationMode
    display_priority: int
    event_priority: int
    updated_at: str
    fetched_at: str
    is_active: bool = True


@dataclass(slots=True)
class ResolvedWeatherAlert:
    alert: WeatherAlert
    effective_escalation_mode: AlertEscalationMode
    effective_display_priority: int


@dataclass(slots=True)
class WeatherProviderState:
    provider_name: str
    provider_display_name: str
    status: str
    available: bool
    configured: bool
    location_label: str
    last_weather_refresh_at: str | None = None
    last_alert_refresh_at: str | None = None
    last_successful_weather_refresh_at: str | None = None
    last_successful_alert_refresh_at: str | None = None
    current_error: str = ""
    updated_at: str = ""


@dataclass(slots=True)
class WeatherRefreshRun:
    id: str
    provider_name: str
    refresh_kind: str
    trigger: str
    status: str
    message: str
    error_message: str
    started_at: str
    completed_at: str | None = None


def normalize_weather_location(location: WeatherLocation) -> WeatherLocation:
    label = location.label.strip()
    latitude = None if location.latitude is None else float(location.latitude)
    longitude = None if location.longitude is None else float(location.longitude)
    if (latitude is None) != (longitude is None):
        raise ValueError("weather_location.latitude and weather_location.longitude must either both be set or both be empty")
    if latitude is not None and not (-90 <= latitude <= 90):
        raise ValueError(f"weather_location.latitude must be between -90 and 90, got {latitude}")
    if longitude is not None and not (-180 <= longitude <= 180):
        raise ValueError(f"weather_location.longitude must be between -180 and 180, got {longitude}")
    return WeatherLocation(label=label, latitude=latitude, longitude=longitude)


def normalize_weather_units(value: str) -> WeatherUnits:
    normalized = value.strip().lower()
    if normalized not in _VALID_UNITS:
        raise ValueError(f"weather_units must be one of {_VALID_UNITS}, got {value!r}")
    return normalized  # type: ignore[return-value]


def normalize_weather_position(value: str) -> WeatherWidgetPosition:
    normalized = value.strip().lower()
    if normalized not in _VALID_POSITIONS:
        raise ValueError(f"weather_position must be one of {_VALID_POSITIONS}, got {value!r}")
    return normalized  # type: ignore[return-value]


def normalize_alert_severity(value: str) -> AlertSeverity:
    normalized = value.strip().lower() or "unknown"
    if normalized not in _VALID_SEVERITIES:
        return "unknown"
    return normalized  # type: ignore[return-value]


def normalize_weather_settings(settings: WeatherSettings) -> WeatherSettings:
    location = normalize_weather_location(settings.weather_location)
    provider = settings.weather_provider.strip().lower() or "nws"
    if settings.weather_enabled and not location.is_configured:
        raise ValueError("weather_location.latitude and weather_location.longitude are required when weather is enabled")
    return WeatherSettings(
        weather_enabled=bool(settings.weather_enabled),
        weather_provider=provider,
        weather_location=location,
        weather_units=normalize_weather_units(settings.weather_units),
        weather_position=normalize_weather_position(settings.weather_position),
        weather_refresh_minutes=max(1, min(int(settings.weather_refresh_minutes), 180)),
        weather_show_precipitation=bool(settings.weather_show_precipitation),
        weather_show_humidity=bool(settings.weather_show_humidity),
        weather_show_wind=bool(settings.weather_show_wind),
        weather_alerts_enabled=bool(settings.weather_alerts_enabled),
        weather_alert_fullscreen_enabled=bool(settings.weather_alert_fullscreen_enabled),
        weather_alert_minimum_severity=normalize_alert_severity(settings.weather_alert_minimum_severity),
        weather_alert_repeat_enabled=bool(settings.weather_alert_repeat_enabled),
        weather_alert_repeat_interval_minutes=max(1, min(int(settings.weather_alert_repeat_interval_minutes), 120)),
        weather_alert_repeat_display_seconds=max(5, min(int(settings.weather_alert_repeat_display_seconds), 300)),
    )


def build_location_key(location: WeatherLocation) -> str:
    normalized = normalize_weather_location(location)
    if not normalized.is_configured:
        return ""
    assert normalized.latitude is not None
    assert normalized.longitude is not None
    return f"{normalized.latitude:.4f},{normalized.longitude:.4f}"


def temperature_c_to_f(value: float | None) -> float | None:
    if value is None:
        return None
    return (value * 9 / 5) + 32


def wind_speed_mph_to_kph(value: float | None) -> float | None:
    if value is None:
        return None
    return value * 1.609344

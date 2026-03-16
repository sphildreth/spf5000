from __future__ import annotations

from dataclasses import asdict
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.models.weather import WeatherLocation, WeatherSettings


class WeatherLocationPayload(BaseModel):
    label: str = Field(default="", max_length=120)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)

    @model_validator(mode="after")
    def require_both_coordinates_or_neither(self) -> "WeatherLocationPayload":
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError("weather_location.latitude and weather_location.longitude must either both be set or both be empty")
        return self

    @classmethod
    def from_domain(cls, location: WeatherLocation) -> "WeatherLocationPayload":
        return cls(label=location.label, latitude=location.latitude, longitude=location.longitude)


class WeatherSettingsResponse(BaseModel):
    weather_enabled: bool
    weather_provider: str
    weather_location: WeatherLocationPayload
    weather_units: Literal["f", "c"]
    weather_position: Literal["top-left", "top-right", "bottom-left", "bottom-right"]
    weather_refresh_minutes: int
    weather_show_precipitation: bool
    weather_show_humidity: bool
    weather_show_wind: bool
    weather_alerts_enabled: bool
    weather_alert_fullscreen_enabled: bool
    weather_alert_minimum_severity: Literal["unknown", "minor", "moderate", "severe", "extreme"]
    weather_alert_repeat_enabled: bool
    weather_alert_repeat_interval_minutes: int
    weather_alert_repeat_display_seconds: int

    @classmethod
    def from_domain(cls, settings: WeatherSettings) -> "WeatherSettingsResponse":
        payload = asdict(settings)
        payload["weather_location"] = WeatherLocationPayload.from_domain(settings.weather_location)
        return cls(**payload)


class WeatherSettingsUpdateRequest(BaseModel):
    weather_enabled: bool
    weather_provider: str = Field(min_length=1, max_length=60)
    weather_location: WeatherLocationPayload
    weather_units: Literal["f", "c"]
    weather_position: Literal["top-left", "top-right", "bottom-left", "bottom-right"]
    weather_refresh_minutes: int = Field(ge=1, le=180)
    weather_show_precipitation: bool
    weather_show_humidity: bool
    weather_show_wind: bool
    weather_alerts_enabled: bool
    weather_alert_fullscreen_enabled: bool
    weather_alert_minimum_severity: Literal["unknown", "minor", "moderate", "severe", "extreme"]
    weather_alert_repeat_enabled: bool
    weather_alert_repeat_interval_minutes: int = Field(ge=1, le=120)
    weather_alert_repeat_display_seconds: int = Field(ge=5, le=300)

    @model_validator(mode="after")
    def require_location_when_enabled(self) -> "WeatherSettingsUpdateRequest":
        if self.weather_enabled and (self.weather_location.latitude is None or self.weather_location.longitude is None):
            raise ValueError("weather_location.latitude and weather_location.longitude are required when weather is enabled")
        return self

    def to_domain(self) -> WeatherSettings:
        return WeatherSettings(
            weather_enabled=self.weather_enabled,
            weather_provider=self.weather_provider,
            weather_location=WeatherLocation(
                label=self.weather_location.label,
                latitude=self.weather_location.latitude,
                longitude=self.weather_location.longitude,
            ),
            weather_units=self.weather_units,
            weather_position=self.weather_position,
            weather_refresh_minutes=self.weather_refresh_minutes,
            weather_show_precipitation=self.weather_show_precipitation,
            weather_show_humidity=self.weather_show_humidity,
            weather_show_wind=self.weather_show_wind,
            weather_alerts_enabled=self.weather_alerts_enabled,
            weather_alert_fullscreen_enabled=self.weather_alert_fullscreen_enabled,
            weather_alert_minimum_severity=self.weather_alert_minimum_severity,
            weather_alert_repeat_enabled=self.weather_alert_repeat_enabled,
            weather_alert_repeat_interval_minutes=self.weather_alert_repeat_interval_minutes,
            weather_alert_repeat_display_seconds=self.weather_alert_repeat_display_seconds,
        )


class WeatherProviderStateResponse(BaseModel):
    provider_name: str
    provider_display_name: str
    status: str
    available: bool
    configured: bool
    location_label: str
    last_weather_refresh_at: str | None
    last_alert_refresh_at: str | None
    last_successful_weather_refresh_at: str | None
    last_successful_alert_refresh_at: str | None
    current_error: str | None
    updated_at: str


class WeatherCurrentConditionsResponse(BaseModel):
    provider_name: str
    provider_display_name: str
    location_label: str
    condition: str
    icon_token: str
    temperature: int | None
    temperature_unit: str
    humidity_percent: int | None
    wind_speed: int | None
    wind_unit: str
    wind_direction: str | None
    precipitation_probability_percent: int | None
    observed_at: str | None
    fetched_at: str
    attribution: str
    is_stale: bool


class WeatherAlertResponse(BaseModel):
    id: str
    provider_name: str
    provider_display_name: str
    event: str
    severity: str
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
    escalation_mode: str
    effective_escalation_mode: str
    display_priority: int
    effective_display_priority: int
    event_priority: int
    is_active: bool
    is_dominant: bool


class WeatherRefreshRunResponse(BaseModel):
    id: str
    provider_name: str
    refresh_kind: str
    trigger: str
    status: str
    message: str
    error_message: str | None
    started_at: str
    completed_at: str | None


class WeatherStatusResponse(BaseModel):
    provider_status: WeatherProviderStateResponse
    current_conditions: WeatherCurrentConditionsResponse | None
    dominant_alert: WeatherAlertResponse | None
    active_alert_count: int
    current_display_action: str
    recent_refresh_runs: list[WeatherRefreshRunResponse]


class WeatherAlertsResponse(BaseModel):
    provider_status: WeatherProviderStateResponse
    alert_count: int
    dominant_alert: WeatherAlertResponse | None
    active_alerts: list[WeatherAlertResponse]


class DisplayWeatherResponse(BaseModel):
    enabled: bool
    position: Literal["top-left", "top-right", "bottom-left", "bottom-right"]
    units: Literal["f", "c"]
    show_precipitation: bool
    show_humidity: bool
    show_wind: bool
    provider_status: WeatherProviderStateResponse
    current_conditions: WeatherCurrentConditionsResponse | None


class DisplayAlertPresentationResponse(BaseModel):
    mode: str
    fallback_mode: str | None
    repeat_interval_minutes: int
    repeat_display_seconds: int
    alert_count: int


class DisplayAlertsResponse(BaseModel):
    provider_status: WeatherProviderStateResponse
    dominant_alert: WeatherAlertResponse | None
    active_alerts: list[WeatherAlertResponse]
    presentation: DisplayAlertPresentationResponse

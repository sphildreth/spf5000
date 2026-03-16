from __future__ import annotations

import threading
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import httpx

from app.models.weather import (
    ResolvedWeatherAlert,
    WeatherCurrentConditions,
    WeatherProviderState,
    WeatherRefreshRun,
    WeatherSettings,
    build_location_key,
    normalize_weather_settings,
    temperature_c_to_f,
    wind_speed_mph_to_kph,
)
from app.repositories.base import utc_now
from app.repositories.weather_repository import WeatherRepository
from app.weather.errors import WeatherConfigurationError, WeatherError
from app.weather.policies import resolve_active_alerts, select_dominant_alert
from app.weather.providers.base import WeatherProvider
from app.weather.providers.nws import NWSWeatherProvider, alert_is_active

_ALERT_REFRESH_MINUTES = 2
_REFRESH_LOCK = threading.Lock()


class WeatherService:
    provider_factories = {
        "nws": NWSWeatherProvider,
    }

    def __init__(self, repo: WeatherRepository | None = None) -> None:
        self.repo = repo or WeatherRepository()

    def get_settings(self) -> WeatherSettings:
        return self.repo.get_settings()

    def update_settings(self, settings: WeatherSettings) -> WeatherSettings:
        normalized = self.repo.update_settings(normalize_weather_settings(settings))
        self._upsert_configuration_state(normalized)
        return normalized

    def refresh_due(self, *, trigger: str = "scheduled") -> dict[str, object]:
        with _REFRESH_LOCK:
            settings = self.get_settings()
            self._upsert_configuration_state(settings)
            if not settings.weather_enabled or not settings.weather_location.is_configured:
                return self.get_status_payload()

            state = self.get_provider_state()
            if self._is_due(state.last_weather_refresh_at, minutes=settings.weather_refresh_minutes):
                self._force_refresh_current_conditions(settings, trigger=trigger)
            if self._is_due(state.last_alert_refresh_at, minutes=_ALERT_REFRESH_MINUTES):
                self._force_refresh_alerts(settings, trigger=trigger)
            return self.get_status_payload()

    def refresh_all(self, *, trigger: str = "manual") -> dict[str, object]:
        with _REFRESH_LOCK:
            settings = self.get_settings()
            if not settings.weather_enabled:
                raise WeatherConfigurationError("Enable weather before requesting a manual weather refresh")
            if not settings.weather_location.is_configured:
                raise WeatherConfigurationError("Set a weather location before requesting a manual weather refresh")
            self._force_refresh_current_conditions(settings, trigger=trigger)
            self._force_refresh_alerts(settings, trigger=trigger)
            return self.get_status_payload()

    def get_provider_state(self) -> WeatherProviderState:
        settings = self.get_settings()
        existing = self.repo.get_provider_state(settings.weather_provider)
        if existing is not None:
            return existing
        provider = self._provider(settings.weather_provider)
        health = provider.health_check(settings.weather_location)
        return WeatherProviderState(
            provider_name=settings.weather_provider,
            provider_display_name=str(health.get("display_name", provider.provider_display_name())),
            status=self._state_status(settings, current_error=""),
            available=bool(health.get("available", True)),
            configured=bool(health.get("configured", settings.weather_location.is_configured)),
            location_label=settings.weather_location.label,
            updated_at=utc_now(),
        )

    def get_status_payload(self) -> dict[str, object]:
        settings = self.get_settings()
        state = self.get_provider_state()
        current = self._current_conditions(settings, state)
        alerts = self._active_alerts(settings)
        resolved_alerts = resolve_active_alerts(alerts, settings)
        dominant = resolved_alerts[0] if resolved_alerts else None
        presentation = self._display_presentation(settings, dominant, len(resolved_alerts))
        return {
            "provider_status": self._provider_state_payload(state),
            "current_conditions": None if current is None else self._conditions_payload(current, settings),
            "dominant_alert": None if dominant is None else self._alert_payload(dominant, dominant=True),
            "active_alert_count": len(resolved_alerts),
            "current_display_action": presentation["mode"],
            "recent_refresh_runs": [
                self._refresh_run_payload(item) for item in self.repo.list_refresh_runs(settings.weather_provider, limit=6)
            ],
        }

    def get_alerts_payload(self) -> dict[str, object]:
        settings = self.get_settings()
        alerts = self._active_alerts(settings)
        resolved_alerts = resolve_active_alerts(alerts, settings)
        dominant = resolved_alerts[0] if resolved_alerts else None
        state = self.get_provider_state()
        return {
            "provider_status": self._provider_state_payload(state),
            "alert_count": len(resolved_alerts),
            "dominant_alert": None if dominant is None else self._alert_payload(dominant, dominant=True),
            "active_alerts": [self._alert_payload(alert, dominant=False) for alert in resolved_alerts],
        }

    def get_display_weather_payload(self) -> dict[str, object]:
        settings = self.get_settings()
        state = self.get_provider_state()
        current = self._current_conditions(settings, state)
        return {
            "enabled": settings.weather_enabled,
            "position": settings.weather_position,
            "units": settings.weather_units,
            "show_precipitation": settings.weather_show_precipitation,
            "show_humidity": settings.weather_show_humidity,
            "show_wind": settings.weather_show_wind,
            "provider_status": self._provider_state_payload(state),
            "current_conditions": None if current is None else self._conditions_payload(current, settings),
        }

    def get_display_alerts_payload(self) -> dict[str, object]:
        settings = self.get_settings()
        alerts = self._active_alerts(settings)
        resolved_alerts = resolve_active_alerts(alerts, settings)
        dominant = resolved_alerts[0] if resolved_alerts else None
        state = self.get_provider_state()
        return {
            "provider_status": self._provider_state_payload(state),
            "dominant_alert": None if dominant is None else self._alert_payload(dominant, dominant=True),
            "active_alerts": [self._alert_payload(alert, dominant=False) for alert in resolved_alerts],
            "presentation": self._display_presentation(settings, dominant, len(resolved_alerts)),
        }

    def _provider(self, provider_name: str) -> WeatherProvider:
        factory = self.provider_factories.get(provider_name)
        if factory is None:
            raise WeatherConfigurationError(f"Unsupported weather provider {provider_name!r}")
        return factory()

    def _upsert_configuration_state(self, settings: WeatherSettings, *, current_error: str | None = None) -> WeatherProviderState:
        provider = self._provider(settings.weather_provider)
        health = provider.health_check(settings.weather_location)
        existing = self.repo.get_provider_state(settings.weather_provider)
        state = WeatherProviderState(
            provider_name=settings.weather_provider,
            provider_display_name=str(health.get("display_name", provider.provider_display_name())),
            status=self._state_status(settings, current_error=current_error if current_error is not None else (existing.current_error if existing else "")),
            available=bool(health.get("available", True)),
            configured=bool(health.get("configured", settings.weather_location.is_configured)),
            location_label=settings.weather_location.label,
            last_weather_refresh_at=None if existing is None else existing.last_weather_refresh_at,
            last_alert_refresh_at=None if existing is None else existing.last_alert_refresh_at,
            last_successful_weather_refresh_at=None if existing is None else existing.last_successful_weather_refresh_at,
            last_successful_alert_refresh_at=None if existing is None else existing.last_successful_alert_refresh_at,
            current_error=current_error if current_error is not None else ("" if existing is None else existing.current_error),
            updated_at=utc_now(),
        )
        return self.repo.upsert_provider_state(state)

    @staticmethod
    def _state_status(settings: WeatherSettings, *, current_error: str) -> str:
        if not settings.weather_enabled:
            return "disabled"
        if not settings.weather_location.is_configured:
            return "unconfigured"
        if current_error:
            return "degraded"
        return "ready"

    def _force_refresh_current_conditions(self, settings: WeatherSettings, *, trigger: str) -> WeatherRefreshRun:
        started_at = utc_now()
        refresh_run = WeatherRefreshRun(
            id=f"weather-refresh-{uuid4().hex[:12]}",
            provider_name=settings.weather_provider,
            refresh_kind="weather",
            trigger=trigger,
            status="running",
            message="Refreshing cached weather conditions",
            error_message="",
            started_at=started_at,
        )
        self.repo.create_refresh_run(refresh_run)
        provider = self._provider(settings.weather_provider)
        state = self.get_provider_state()
        try:
            current = provider.get_current_conditions(settings.weather_location)
            current.fetched_at = started_at
            self.repo.upsert_current_conditions(current)
            state.status = self._state_status(settings, current_error="")
            state.provider_display_name = current.provider_display_name
            state.location_label = current.location_label
            state.last_weather_refresh_at = started_at
            state.last_successful_weather_refresh_at = started_at
            state.current_error = ""
            state.updated_at = started_at
            self.repo.upsert_provider_state(state)
            refresh_run.status = "completed"
            refresh_run.message = "Weather conditions refreshed"
            refresh_run.completed_at = started_at
            return self.repo.update_refresh_run(refresh_run)
        except (WeatherError, httpx.HTTPError, ValueError) as exc:
            state.status = self._state_status(settings, current_error=str(exc))
            state.last_weather_refresh_at = started_at
            state.current_error = str(exc)
            state.updated_at = started_at
            self.repo.upsert_provider_state(state)
            refresh_run.status = "failed"
            refresh_run.message = "Weather conditions refresh failed"
            refresh_run.error_message = str(exc)
            refresh_run.completed_at = started_at
            return self.repo.update_refresh_run(refresh_run)

    def _force_refresh_alerts(self, settings: WeatherSettings, *, trigger: str) -> WeatherRefreshRun:
        started_at = utc_now()
        refresh_run = WeatherRefreshRun(
            id=f"weather-refresh-{uuid4().hex[:12]}",
            provider_name=settings.weather_provider,
            refresh_kind="alerts",
            trigger=trigger,
            status="running",
            message="Refreshing cached weather alerts",
            error_message="",
            started_at=started_at,
        )
        self.repo.create_refresh_run(refresh_run)
        provider = self._provider(settings.weather_provider)
        state = self.get_provider_state()
        location_key = build_location_key(settings.weather_location)
        try:
            alerts = provider.get_active_alerts(settings.weather_location)
            self.repo.replace_active_alerts(settings.weather_provider, location_key, alerts)
            state.status = self._state_status(settings, current_error="")
            state.last_alert_refresh_at = started_at
            state.last_successful_alert_refresh_at = started_at
            state.current_error = ""
            state.updated_at = started_at
            self.repo.upsert_provider_state(state)
            refresh_run.status = "completed"
            refresh_run.message = f"Weather alerts refreshed ({len(alerts)} active)"
            refresh_run.completed_at = started_at
            return self.repo.update_refresh_run(refresh_run)
        except (WeatherError, httpx.HTTPError, ValueError) as exc:
            state.status = self._state_status(settings, current_error=str(exc))
            state.last_alert_refresh_at = started_at
            state.current_error = str(exc)
            state.updated_at = started_at
            self.repo.upsert_provider_state(state)
            refresh_run.status = "failed"
            refresh_run.message = "Weather alerts refresh failed"
            refresh_run.error_message = str(exc)
            refresh_run.completed_at = started_at
            return self.repo.update_refresh_run(refresh_run)

    def _current_conditions(
        self,
        settings: WeatherSettings,
        state: WeatherProviderState,
    ) -> WeatherCurrentConditions | None:
        location_key = build_location_key(settings.weather_location)
        if not location_key:
            return None
        current = self.repo.get_current_conditions(settings.weather_provider, location_key)
        if current is None:
            return None
        if self._is_stale(state.last_successful_weather_refresh_at, minutes=settings.weather_refresh_minutes * 2):
            current.is_stale = True
        return current

    def _active_alerts(self, settings: WeatherSettings) -> list[object]:
        location_key = build_location_key(settings.weather_location)
        if not location_key:
            return []
        now = datetime.now(UTC)
        return [alert for alert in self.repo.list_alerts(settings.weather_provider, location_key) if alert_is_active(alert, now=now)]

    @staticmethod
    def _is_due(last_refresh_at: str | None, *, minutes: int) -> bool:
        if not last_refresh_at:
            return True
        try:
            last_refresh = datetime.fromisoformat(last_refresh_at.replace("Z", "+00:00"))
        except ValueError:
            return True
        if last_refresh.tzinfo is None:
            last_refresh = last_refresh.replace(tzinfo=UTC)
        return datetime.now(UTC) - last_refresh >= timedelta(minutes=minutes)

    @staticmethod
    def _is_stale(last_success_at: str | None, *, minutes: int) -> bool:
        if not last_success_at:
            return True
        try:
            last_success = datetime.fromisoformat(last_success_at.replace("Z", "+00:00"))
        except ValueError:
            return True
        if last_success.tzinfo is None:
            last_success = last_success.replace(tzinfo=UTC)
        return datetime.now(UTC) - last_success >= timedelta(minutes=minutes)

    def _conditions_payload(self, current: WeatherCurrentConditions, settings: WeatherSettings) -> dict[str, object]:
        temperature = current.temperature_c if settings.weather_units == "c" else temperature_c_to_f(current.temperature_c)
        wind_speed = current.wind_speed_mph if settings.weather_units == "f" else wind_speed_mph_to_kph(current.wind_speed_mph)
        return {
            "provider_name": current.provider_name,
            "provider_display_name": current.provider_display_name,
            "location_label": current.location_label,
            "condition": current.condition,
            "icon_token": current.icon_token,
            "temperature": None if temperature is None else round(temperature),
            "temperature_unit": "C" if settings.weather_units == "c" else "F",
            "humidity_percent": current.humidity_percent,
            "wind_speed": None if wind_speed is None else round(wind_speed),
            "wind_unit": "km/h" if settings.weather_units == "c" else "mph",
            "wind_direction": self._wind_direction_label(current.wind_direction),
            "precipitation_probability_percent": current.precipitation_probability_percent,
            "observed_at": current.observed_at,
            "fetched_at": current.fetched_at,
            "attribution": current.attribution,
            "is_stale": current.is_stale,
        }

    def _provider_state_payload(self, state: WeatherProviderState) -> dict[str, object]:
        return {
            "provider_name": state.provider_name,
            "provider_display_name": state.provider_display_name,
            "status": state.status,
            "available": state.available,
            "configured": state.configured,
            "location_label": state.location_label,
            "last_weather_refresh_at": state.last_weather_refresh_at,
            "last_alert_refresh_at": state.last_alert_refresh_at,
            "last_successful_weather_refresh_at": state.last_successful_weather_refresh_at,
            "last_successful_alert_refresh_at": state.last_successful_alert_refresh_at,
            "current_error": state.current_error or None,
            "updated_at": state.updated_at,
        }

    def _alert_payload(self, resolved: ResolvedWeatherAlert, *, dominant: bool) -> dict[str, object]:
        alert = resolved.alert
        return {
            "id": alert.id,
            "provider_name": alert.provider_name,
            "provider_display_name": alert.provider_display_name,
            "event": alert.event,
            "severity": alert.severity,
            "certainty": alert.certainty,
            "urgency": alert.urgency,
            "headline": alert.headline,
            "description": alert.description,
            "instruction": alert.instruction,
            "area": alert.area,
            "status": alert.status,
            "issued_at": alert.issued_at,
            "effective_at": alert.effective_at,
            "expires_at": alert.expires_at,
            "ends_at": alert.ends_at,
            "attribution": alert.attribution,
            "escalation_mode": alert.escalation_mode,
            "effective_escalation_mode": resolved.effective_escalation_mode,
            "display_priority": alert.display_priority,
            "effective_display_priority": resolved.effective_display_priority,
            "event_priority": alert.event_priority,
            "is_active": alert.is_active,
            "is_dominant": dominant,
        }

    @staticmethod
    def _refresh_run_payload(refresh_run: WeatherRefreshRun) -> dict[str, object]:
        return {
            "id": refresh_run.id,
            "provider_name": refresh_run.provider_name,
            "refresh_kind": refresh_run.refresh_kind,
            "trigger": refresh_run.trigger,
            "status": refresh_run.status,
            "message": refresh_run.message,
            "error_message": refresh_run.error_message or None,
            "started_at": refresh_run.started_at,
            "completed_at": refresh_run.completed_at,
        }

    def _display_presentation(
        self,
        settings: WeatherSettings,
        dominant: ResolvedWeatherAlert | None,
        alert_count: int,
    ) -> dict[str, object]:
        if dominant is None:
            return {
                "mode": "none",
                "fallback_mode": None,
                "repeat_interval_minutes": settings.weather_alert_repeat_interval_minutes,
                "repeat_display_seconds": settings.weather_alert_repeat_display_seconds,
                "alert_count": alert_count,
            }
        fallback_mode = "banner" if dominant.effective_escalation_mode == "fullscreen_repeat" else None
        return {
            "mode": dominant.effective_escalation_mode,
            "fallback_mode": fallback_mode,
            "repeat_interval_minutes": settings.weather_alert_repeat_interval_minutes,
            "repeat_display_seconds": settings.weather_alert_repeat_display_seconds,
            "alert_count": alert_count,
        }

    @staticmethod
    def _wind_direction_label(value: str | None) -> str | None:
        if not value:
            return None
        try:
            degrees = float(value)
        except ValueError:
            return value
        directions = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
        index = int((degrees + 22.5) // 45) % len(directions)
        return directions[index]

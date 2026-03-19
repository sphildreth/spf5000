from __future__ import annotations

import hashlib
import threading
from datetime import UTC, datetime
from typing import Any

import httpx

from app.core.config import settings
from app.models.weather import (
    WeatherAlert,
    WeatherCurrentConditions,
    WeatherLocation,
    build_location_key,
    normalize_alert_severity,
)
from app.repositories.base import utc_now
from app.weather.errors import WeatherConfigurationError, WeatherProviderError
from app.weather.policies import event_priority, resolve_default_escalation_mode

POINTS_URL = "https://api.weather.gov/points/{latitude},{longitude}"
ALERTS_URL = "https://api.weather.gov/alerts/active"

_default_timeout = httpx.Timeout(20.0, connect=10.0)
_client_lock = threading.Lock()
_shared_client: httpx.Client | None = None


def _get_shared_client() -> httpx.Client:
    global _shared_client
    with _client_lock:
        if _shared_client is None:
            _shared_client = httpx.Client(
                timeout=_default_timeout,
                follow_redirects=True,
                limits=httpx.Limits(max_keepalive_connections=2, max_connections=4),
            )
        return _shared_client


class NWSWeatherProvider:
    def provider_name(self) -> str:
        return "nws"

    def provider_display_name(self) -> str:
        return "National Weather Service"

    def health_check(self, location: WeatherLocation | None) -> dict[str, Any]:
        configured = bool(location and location.is_configured)
        return {
            "provider": self.provider_name(),
            "display_name": self.provider_display_name(),
            "available": True,
            "configured": configured,
        }

    def get_current_conditions(
        self, location: WeatherLocation
    ) -> WeatherCurrentConditions:
        self._ensure_location(location)
        location_key = build_location_key(location)
        points_payload = self._get_json(
            POINTS_URL.format(latitude=location.latitude, longitude=location.longitude)
        )
        properties = self._require_dict(
            points_payload.get("properties"), "NWS points response missing properties"
        )
        observation_stations_url = self._require_string(
            properties.get("observationStations"),
            "NWS points response missing observationStations URL",
        )
        forecast_hourly_url = self._require_string(
            properties.get("forecastHourly"),
            "NWS points response missing forecastHourly URL",
        )
        relative_location = self._parse_relative_location(
            properties.get("relativeLocation")
        )
        location_label = location.label or relative_location or location_key

        observation_payload: dict[str, Any] | None = None
        observation_station_id = self._first_station_id(observation_stations_url)
        if observation_station_id:
            observation_payload = self._get_json(
                f"https://api.weather.gov/stations/{observation_station_id}/observations/latest"
            )
        forecast_payload = self._get_json(forecast_hourly_url)

        observation_props = (
            self._require_dict(
                observation_payload.get("properties"),
                "NWS observation response missing properties",
            )
            if observation_payload
            else {}
        )
        current_period = self._first_forecast_period(forecast_payload)

        temperature_c = self._measurement_to_celsius(
            observation_props.get("temperature")
        )
        if temperature_c is None and current_period is not None:
            temperature_c = self._forecast_temperature_to_celsius(current_period)

        humidity_percent = self._optional_int(
            self._measurement_value(observation_props.get("relativeHumidity"))
        )
        wind_speed_mph = self._measurement_to_mph(observation_props.get("windSpeed"))
        if wind_speed_mph is None and current_period is not None:
            wind_speed_mph = self._wind_speed_string_to_mph(
                self._optional_string(current_period.get("windSpeed"))
            )

        precipitation_probability_percent = None
        if current_period is not None:
            precipitation_probability_percent = self._optional_int(
                self._measurement_value(
                    current_period.get("probabilityOfPrecipitation")
                )
            )

        condition = (
            self._optional_string(observation_props.get("textDescription"))
            or self._optional_string(
                None if current_period is None else current_period.get("shortForecast")
            )
            or "Unavailable"
        )
        icon_token = self._icon_token(
            self._optional_string(observation_props.get("icon"))
            or self._optional_string(
                None if current_period is None else current_period.get("icon")
            ),
            condition,
        )
        wind_direction = (
            self._optional_string(
                observation_props.get("windDirection", {}).get("value")
            )
            if isinstance(
                observation_props.get("windDirection"),
                dict,
            )
            else self._optional_string(observation_props.get("windDirection"))
        )

        return WeatherCurrentConditions(
            provider_name=self.provider_name(),
            provider_display_name=self.provider_display_name(),
            location_key=location_key,
            location_label=location_label,
            condition=condition,
            icon_token=icon_token,
            temperature_c=temperature_c,
            humidity_percent=humidity_percent,
            wind_speed_mph=wind_speed_mph,
            wind_direction=wind_direction,
            precipitation_probability_percent=precipitation_probability_percent,
            observed_at=self._optional_string(observation_props.get("timestamp"))
            or self._optional_string(
                None if current_period is None else current_period.get("startTime")
            ),
            fetched_at=utc_now(),
        )

    def get_active_alerts(self, location: WeatherLocation) -> list[WeatherAlert]:
        self._ensure_location(location)
        location_key = build_location_key(location)
        payload = self._get_json(ALERTS_URL, params={"point": location_key})
        features = payload.get("features")
        if not isinstance(features, list):
            return []
        fetched_at = utc_now()
        alerts: list[WeatherAlert] = []
        for feature in features:
            if not isinstance(feature, dict):
                continue
            properties = feature.get("properties")
            if not isinstance(properties, dict):
                continue
            event = self._optional_string(properties.get("event")) or "Weather Alert"
            severity = normalize_alert_severity(
                self._optional_string(properties.get("severity")) or "unknown"
            )
            alert_id = self._optional_string(
                feature.get("id")
            ) or self._optional_string(properties.get("id"))
            source_alert_id = (
                alert_id
                or hashlib.sha256(
                    f"{event}|{properties.get('sent')}|{properties.get('headline')}".encode(
                        "utf-8"
                    )
                ).hexdigest()
            )
            escalation_mode = resolve_default_escalation_mode(
                event, self._optional_string(properties.get("status"))
            )
            event_prio = event_priority(event)
            display_priority = (
                event_prio * 10_000
                + {
                    "ignore": 0,
                    "badge": 100_000,
                    "banner": 200_000,
                    "fullscreen": 300_000,
                    "fullscreen_repeat": 400_000,
                }[escalation_mode]
            )
            alerts.append(
                WeatherAlert(
                    id=f"weather-alert-{hashlib.sha256(source_alert_id.encode('utf-8')).hexdigest()[:16]}",
                    provider_name=self.provider_name(),
                    provider_display_name=self.provider_display_name(),
                    location_key=location_key,
                    source_alert_id=source_alert_id,
                    event=event,
                    severity=severity,
                    certainty=self._optional_string(properties.get("certainty"))
                    or "Unknown",
                    urgency=self._optional_string(properties.get("urgency"))
                    or "Unknown",
                    headline=self._optional_string(properties.get("headline")) or event,
                    description=self._optional_string(properties.get("description"))
                    or "",
                    instruction=self._optional_string(properties.get("instruction"))
                    or "",
                    area=self._optional_string(properties.get("areaDesc"))
                    or location.label
                    or location_key,
                    status=self._optional_string(properties.get("status")) or "Actual",
                    issued_at=self._optional_string(properties.get("sent")),
                    effective_at=self._optional_string(properties.get("effective")),
                    expires_at=self._optional_string(properties.get("expires")),
                    ends_at=self._optional_string(properties.get("ends")),
                    attribution=self.provider_display_name(),
                    escalation_mode=escalation_mode,  # type: ignore[arg-type]
                    display_priority=display_priority,
                    event_priority=event_prio,
                    updated_at=fetched_at,
                    fetched_at=fetched_at,
                    is_active=True,
                )
            )
        return alerts

    def _get_json(
        self, url: str, *, params: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        headers = {
            "Accept": "application/geo+json, application/json",
            "User-Agent": f"{settings.app_name}/{settings.app_version} (weather cache; admin-managed display)",
        }
        last_exc: Exception | None = None
        last_response: httpx.Response | None = None
        for attempt in range(4):
            try:
                client = _get_shared_client()
                last_response = client.get(url, params=params, headers=headers)
                try:
                    if last_response.status_code not in {429, 500, 502, 503, 504}:
                        break
                    last_exc = WeatherProviderError(
                        f"NWS request failed with status {last_response.status_code} for {url}"
                    )
                finally:
                    if last_response.status_code in {429, 500, 502, 503, 504}:
                        last_response.close()
            except (httpx.ConnectError, httpx.TimeoutException) as exc:
                last_exc = exc
            if attempt < 3:
                import time

                time.sleep(2.0**attempt)
        else:
            raise last_exc or WeatherProviderError(f"NWS request failed for {url}")
        
        try:
            if last_response.status_code >= 400:
                raise WeatherProviderError(
                    f"NWS request failed with status {last_response.status_code} for {url}"
                )
            try:
                payload = last_response.json()
            except ValueError as exc:
                raise WeatherProviderError(f"NWS returned invalid JSON for {url}") from exc
            if not isinstance(payload, dict):
                raise WeatherProviderError(f"NWS returned a non-object payload for {url}")
            return payload
        finally:
            last_response.close()

    def _first_station_id(self, url: str) -> str | None:
        payload = self._get_json(url)
        features = payload.get("features")
        if not isinstance(features, list) or not features:
            return None
        first_feature = features[0]
        if isinstance(first_feature, str):
            return first_feature.rstrip("/").split("/")[-1]
        if isinstance(first_feature, dict):
            if isinstance(first_feature.get("id"), str):
                return str(first_feature["id"]).rstrip("/").split("/")[-1]
            properties = first_feature.get("properties")
            if isinstance(properties, dict) and isinstance(
                properties.get("stationIdentifier"), str
            ):
                return str(properties["stationIdentifier"])
        return None

    @staticmethod
    def _parse_relative_location(value: object) -> str | None:
        if not isinstance(value, dict):
            return None
        properties = value.get("properties")
        if not isinstance(properties, dict):
            return None
        city = properties.get("city")
        state = properties.get("state")
        if isinstance(city, str) and isinstance(state, str):
            return f"{city}, {state}"
        return None

    @staticmethod
    def _first_forecast_period(payload: dict[str, Any]) -> dict[str, Any] | None:
        properties = payload.get("properties")
        if not isinstance(properties, dict):
            return None
        periods = properties.get("periods")
        if not isinstance(periods, list) or not periods:
            return None
        first = periods[0]
        return first if isinstance(first, dict) else None

    @staticmethod
    def _measurement_value(value: object) -> float | int | None:
        if not isinstance(value, dict):
            return None
        raw = value.get("value")
        if raw is None:
            return None
        if isinstance(raw, (int, float)):
            return raw
        return None

    @staticmethod
    def _measurement_to_celsius(value: object) -> float | None:
        if not isinstance(value, dict):
            return None
        raw = value.get("value")
        if raw is None:
            return None
        numeric = float(raw)
        unit_code = str(value.get("unitCode") or "")
        if unit_code.endswith("degF"):
            return (numeric - 32) * 5 / 9
        return numeric

    @staticmethod
    def _measurement_to_mph(value: object) -> float | None:
        if not isinstance(value, dict):
            return None
        raw = value.get("value")
        if raw is None:
            return None
        numeric = float(raw)
        unit_code = str(value.get("unitCode") or "")
        if unit_code.endswith("km_h-1"):
            return numeric * 0.621371
        if unit_code.endswith("m_s-1"):
            return numeric * 2.23694
        if unit_code.endswith("kn"):
            return numeric * 1.15078
        return numeric

    @staticmethod
    def _forecast_temperature_to_celsius(period: dict[str, Any]) -> float | None:
        raw = period.get("temperature")
        if raw is None:
            return None
        numeric = float(raw)
        unit = str(period.get("temperatureUnit") or "F").upper()
        if unit == "F":
            return (numeric - 32) * 5 / 9
        return numeric

    @staticmethod
    def _wind_speed_string_to_mph(value: str | None) -> float | None:
        if not value:
            return None
        token = value.strip().split(" ")[0]
        if "-" in token:
            token = token.split("-")[-1]
        try:
            return float(token)
        except ValueError:
            return None

    @staticmethod
    def _icon_token(icon_url: str | None, condition: str) -> str:
        normalized = ((icon_url or "") + " " + (condition or "")).lower()
        if any(
            token in normalized for token in ("tornado", "thunder", "tsra", "storm")
        ):
            return "thunderstorm"
        if any(token in normalized for token in ("snow", "blizzard", "sleet")):
            return "snow"
        if any(token in normalized for token in ("rain", "showers", "drizzle")):
            return "rain"
        if any(token in normalized for token in ("fog", "mist", "haze")):
            return "fog"
        if any(token in normalized for token in ("wind", "breezy")):
            return "wind"
        if any(token in normalized for token in ("ice", "frzr", "freezing")):
            return "ice"
        if any(token in normalized for token in ("few", "sct", "partly")):
            return "partly-cloudy"
        if any(token in normalized for token in ("ovc", "bkn", "cloud", "overcast")):
            return "cloudy"
        if any(token in normalized for token in ("clear", "skc", "sun")):
            return "sunny"
        return "cloudy"

    @staticmethod
    def _optional_int(value: float | int | None) -> int | None:
        if value is None:
            return None
        return int(round(float(value)))

    @staticmethod
    def _optional_string(value: object) -> str | None:
        if value is None:
            return None
        string_value = str(value).strip()
        return string_value or None

    @staticmethod
    def _require_dict(value: object, message: str) -> dict[str, Any]:
        if not isinstance(value, dict):
            raise WeatherProviderError(message)
        return value

    @staticmethod
    def _require_string(value: object, message: str) -> str:
        if not isinstance(value, str) or not value:
            raise WeatherProviderError(message)
        return value

    @staticmethod
    def _ensure_location(location: WeatherLocation) -> None:
        if not location.is_configured:
            raise WeatherConfigurationError(
                "Weather location must include both latitude and longitude"
            )


def alert_is_active(alert: WeatherAlert, *, now: datetime | None = None) -> bool:
    if not alert.is_active:
        return False
    if not alert.expires_at:
        return True
    try:
        expires_at = datetime.fromisoformat(alert.expires_at.replace("Z", "+00:00"))
    except ValueError:
        return True
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    effective_now = now or datetime.now(UTC)
    return expires_at > effective_now

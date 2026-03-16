from __future__ import annotations

from app.models.weather import WeatherAlert, WeatherCurrentConditions, WeatherLocation, WeatherProviderState, WeatherSettings
from app.repositories.base import utc_now
from app.repositories.weather_repository import WeatherRepository
from app.services.weather_service import WeatherService
from app.weather.policies import resolve_active_alerts, select_dominant_alert


def _weather_settings(*, units: str = "f") -> WeatherSettings:
    return WeatherSettings(
        weather_enabled=True,
        weather_provider="nws",
        weather_location=WeatherLocation(label="Overland Park, KS", latitude=38.9822, longitude=-94.6708),
        weather_units=units,  # type: ignore[arg-type]
        weather_position="top-right",
        weather_refresh_minutes=15,
        weather_show_precipitation=True,
        weather_show_humidity=True,
        weather_show_wind=True,
        weather_alerts_enabled=True,
        weather_alert_fullscreen_enabled=True,
        weather_alert_minimum_severity="minor",
        weather_alert_repeat_enabled=True,
        weather_alert_repeat_interval_minutes=5,
        weather_alert_repeat_display_seconds=20,
    )


def _current_conditions() -> WeatherCurrentConditions:
    return WeatherCurrentConditions(
        provider_name="nws",
        provider_display_name="National Weather Service",
        location_key="38.9822,-94.6708",
        location_label="Overland Park, KS",
        condition="Partly Cloudy",
        icon_token="partly-cloudy",
        temperature_c=20.0,
        humidity_percent=65,
        wind_speed_mph=12.0,
        wind_direction="180",
        precipitation_probability_percent=30,
        observed_at="2026-03-16T18:00:00+00:00",
        fetched_at=utc_now(),
    )


def _alert(
    *,
    event: str,
    severity: str,
    escalation_mode: str,
    display_priority: int,
    event_priority: int,
    issued_at: str,
) -> WeatherAlert:
    return WeatherAlert(
        id=f"alert-{event.lower().replace(' ', '-')}-{severity.lower()}",
        provider_name="nws",
        provider_display_name="National Weather Service",
        location_key="38.9822,-94.6708",
        source_alert_id=f"src-{event.lower().replace(' ', '-')}",
        event=event,
        severity=severity,  # type: ignore[arg-type]
        certainty="Likely",
        urgency="Immediate",
        headline=f"{event} for Johnson County",
        description=f"{event} description",
        instruction="Take action immediately",
        area="Johnson County, KS",
        status="Actual",
        issued_at=issued_at,
        effective_at=issued_at,
        expires_at="2099-01-01T01:00:00+00:00",
        ends_at=None,
        attribution="National Weather Service",
        escalation_mode=escalation_mode,  # type: ignore[arg-type]
        display_priority=display_priority,
        event_priority=event_priority,
        updated_at=issued_at,
        fetched_at=issued_at,
        is_active=True,
    )


def _seed_weather_cache(repo: WeatherRepository, *, units: str = "f") -> None:
    repo.update_settings(_weather_settings(units=units))
    repo.upsert_provider_state(
        WeatherProviderState(
            provider_name="nws",
            provider_display_name="National Weather Service",
            status="ready",
            available=True,
            configured=True,
            location_label="Overland Park, KS",
            last_weather_refresh_at="2026-03-16T18:00:00+00:00",
            last_alert_refresh_at="2026-03-16T18:00:00+00:00",
            last_successful_weather_refresh_at="2026-03-16T18:00:00+00:00",
            last_successful_alert_refresh_at="2026-03-16T18:00:00+00:00",
            current_error="",
            updated_at="2026-03-16T18:00:00+00:00",
        )
    )
    repo.upsert_current_conditions(_current_conditions())
    repo.replace_active_alerts(
        "nws",
        "38.9822,-94.6708",
        [
            _alert(
                event="Tornado Warning",
                severity="extreme",
                escalation_mode="fullscreen_repeat",
                display_priority=500000,
                event_priority=100,
                issued_at="2026-03-16T18:00:00+00:00",
            ),
            _alert(
                event="Wind Advisory",
                severity="moderate",
                escalation_mode="banner",
                display_priority=200000,
                event_priority=56,
                issued_at="2026-03-16T17:00:00+00:00",
            ),
        ],
    )


def test_weather_settings_endpoint_rejects_missing_coordinates(test_client) -> None:
    response = test_client.put(
        "/api/weather/settings",
        json={
            "weather_enabled": True,
            "weather_provider": "nws",
            "weather_location": {"label": "Missing coords", "latitude": None, "longitude": None},
            "weather_units": "f",
            "weather_position": "top-right",
            "weather_refresh_minutes": 15,
            "weather_show_precipitation": True,
            "weather_show_humidity": True,
            "weather_show_wind": True,
            "weather_alerts_enabled": True,
            "weather_alert_fullscreen_enabled": True,
            "weather_alert_minimum_severity": "minor",
            "weather_alert_repeat_enabled": True,
            "weather_alert_repeat_interval_minutes": 5,
            "weather_alert_repeat_display_seconds": 20,
        },
    )
    assert response.status_code == 422


def test_weather_repository_persists_settings_and_cached_alerts(test_client) -> None:
    repo = WeatherRepository()
    _seed_weather_cache(repo)

    settings = repo.get_settings()
    assert settings.weather_enabled is True
    assert settings.weather_location.label == "Overland Park, KS"

    current = repo.get_current_conditions("nws", "38.9822,-94.6708")
    assert current is not None
    assert current.icon_token == "partly-cloudy"

    alerts = repo.list_alerts("nws", "38.9822,-94.6708")
    assert len(alerts) == 2
    assert alerts[0].event == "Tornado Warning"


def test_display_weather_endpoint_formats_units_from_cached_conditions(test_client) -> None:
    repo = WeatherRepository()
    _seed_weather_cache(repo, units="c")

    response_c = test_client.get("/api/display/weather")
    assert response_c.status_code == 200
    body_c = response_c.json()
    assert body_c["current_conditions"]["temperature"] == 20
    assert body_c["current_conditions"]["temperature_unit"] == "C"
    assert body_c["current_conditions"]["wind_speed"] == 19
    assert body_c["current_conditions"]["wind_unit"] == "km/h"

    repo.update_settings(_weather_settings(units="f"))
    response_f = test_client.get("/api/display/weather")
    assert response_f.status_code == 200
    body_f = response_f.json()
    assert body_f["current_conditions"]["temperature"] == 68
    assert body_f["current_conditions"]["temperature_unit"] == "F"
    assert body_f["current_conditions"]["wind_speed"] == 12
    assert body_f["current_conditions"]["wind_unit"] == "mph"


def test_display_alerts_endpoint_returns_dominant_alert_and_repeat_metadata(test_client) -> None:
    repo = WeatherRepository()
    _seed_weather_cache(repo)

    response = test_client.get("/api/display/alerts")
    assert response.status_code == 200
    body = response.json()
    assert body["dominant_alert"]["event"] == "Tornado Warning"
    assert body["dominant_alert"]["effective_escalation_mode"] == "fullscreen_repeat"
    assert body["presentation"]["mode"] == "fullscreen_repeat"
    assert body["presentation"]["fallback_mode"] == "banner"
    assert body["presentation"]["repeat_interval_minutes"] == 5
    assert body["presentation"]["repeat_display_seconds"] == 20
    assert len(body["active_alerts"]) == 2


def test_alert_priority_prefers_escalation_then_severity_then_event_then_newest() -> None:
    settings = _weather_settings()
    alerts = [
        _alert(
            event="Wind Advisory",
            severity="extreme",
            escalation_mode="banner",
            display_priority=200000,
            event_priority=56,
            issued_at="2026-03-16T19:00:00+00:00",
        ),
        _alert(
            event="Severe Thunderstorm Warning",
            severity="severe",
            escalation_mode="fullscreen",
            display_priority=300000,
            event_priority=85,
            issued_at="2026-03-16T18:00:00+00:00",
        ),
        _alert(
            event="Tornado Warning",
            severity="extreme",
            escalation_mode="fullscreen_repeat",
            display_priority=500000,
            event_priority=100,
            issued_at="2026-03-16T17:00:00+00:00",
        ),
    ]

    dominant = select_dominant_alert(alerts, settings)
    assert dominant is not None
    assert dominant.alert.event == "Tornado Warning"

    resolved = resolve_active_alerts(alerts, settings)
    assert [item.alert.event for item in resolved][:2] == ["Tornado Warning", "Severe Thunderstorm Warning"]


def test_repeat_disabled_degrades_fullscreen_repeat_to_fullscreen() -> None:
    settings = _weather_settings()
    settings.weather_alert_repeat_enabled = False
    alert = _alert(
        event="Tornado Warning",
        severity="extreme",
        escalation_mode="fullscreen_repeat",
        display_priority=500000,
        event_priority=100,
        issued_at="2026-03-16T18:00:00+00:00",
    )

    dominant = select_dominant_alert([alert], settings)
    assert dominant is not None
    assert dominant.effective_escalation_mode == "fullscreen"


def test_manual_weather_refresh_uses_fake_provider_and_updates_cached_state(test_client, monkeypatch) -> None:
    class FakeWeatherProvider:
        def provider_name(self) -> str:
            return "nws"

        def provider_display_name(self) -> str:
            return "National Weather Service"

        def health_check(self, location: WeatherLocation | None) -> dict[str, object]:
            return {
                "provider": "nws",
                "display_name": "National Weather Service",
                "available": True,
                "configured": bool(location and location.is_configured),
            }

        def get_current_conditions(self, location: WeatherLocation) -> WeatherCurrentConditions:
            assert location.label == "Overland Park, KS"
            return _current_conditions()

        def get_active_alerts(self, location: WeatherLocation) -> list[WeatherAlert]:
            assert location.label == "Overland Park, KS"
            return [
                _alert(
                    event="Tornado Warning",
                    severity="extreme",
                    escalation_mode="fullscreen_repeat",
                    display_priority=500000,
                    event_priority=100,
                    issued_at="2026-03-16T18:00:00+00:00",
                )
            ]

    monkeypatch.setitem(WeatherService.provider_factories, "nws", lambda: FakeWeatherProvider())
    repo = WeatherRepository()
    repo.update_settings(_weather_settings())

    response = test_client.post("/api/weather/refresh")
    assert response.status_code == 200
    body = response.json()
    assert body["provider_status"]["status"] == "ready"
    assert body["current_conditions"]["temperature"] == 68
    assert body["dominant_alert"]["event"] == "Tornado Warning"

    display_weather = test_client.get("/api/display/weather")
    assert display_weather.status_code == 200
    assert display_weather.json()["current_conditions"]["location_label"] == "Overland Park, KS"

    display_alerts = test_client.get("/api/display/alerts")
    assert display_alerts.status_code == 200
    assert display_alerts.json()["presentation"]["mode"] == "fullscreen_repeat"


def test_weather_routes_require_auth(fresh_client) -> None:
    fresh_client.post(
        "/api/setup",
        json={"username": "admin", "password": "strongpass1", "confirm_password": "strongpass1"},
    )
    fresh_client.post("/api/auth/logout")

    assert fresh_client.get("/api/weather/settings").status_code == 401
    assert fresh_client.get("/api/weather/status").status_code == 401

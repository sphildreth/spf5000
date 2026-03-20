from __future__ import annotations

from typing import Callable, TypeVar

import structlog

from app.db.bootstrap import INDEX_STATEMENTS, TABLE_STATEMENTS
from app.db.connection import (
    exclusive_database_access,
    get_connection,
    is_null_connection,
    reset_connection_state,
)
from app.db.recovery import is_recoverable_database_error
from app.models.weather import (
    WeatherAlert,
    WeatherCurrentConditions,
    WeatherLocation,
    WeatherProviderState,
    WeatherRefreshRun,
    WeatherSettings,
    normalize_weather_settings,
)
from app.repositories.base import bool_to_int, int_to_bool, json_dumps, json_loads, row_to_dict, rows_to_dicts, utc_now

_WEATHER_SETTING_KEYS = (
    "weather_enabled",
    "weather_provider",
    "weather_location",
    "weather_units",
    "weather_position",
    "weather_refresh_minutes",
    "weather_show_precipitation",
    "weather_show_humidity",
    "weather_show_wind",
    "weather_alerts_enabled",
    "weather_alert_fullscreen_enabled",
    "weather_alert_minimum_severity",
    "weather_alert_repeat_enabled",
    "weather_alert_repeat_interval_minutes",
    "weather_alert_repeat_display_seconds",
)
_DEFAULT_SETTINGS = WeatherSettings()
_REFRESH_RUNS_TABLE = "weather_refresh_runs"
_REFRESH_RUNS_INDEXES = ("idx_weather_refresh_runs_provider_started",)
_T = TypeVar("_T")


LOGGER = structlog.get_logger(__name__)


class WeatherRepository:
    def get_settings(self) -> WeatherSettings:
        with get_connection() as conn:
            if is_null_connection(conn):
                return _DEFAULT_SETTINGS
            cursor = conn.execute(
                "select key, value from settings where key in (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                _WEATHER_SETTING_KEYS,
            )
            values = {key: value for key, value in cursor.fetchall()}
        location_payload = json_loads(values.get("weather_location"), default={})
        if not isinstance(location_payload, dict):
            location_payload = {}
        return normalize_weather_settings(
            WeatherSettings(
                weather_enabled=bool(int(values.get("weather_enabled", "0"))),
                weather_provider=str(values.get("weather_provider", _DEFAULT_SETTINGS.weather_provider)),
                weather_location=WeatherLocation(
                    label=str(location_payload.get("label", "")),
                    latitude=None if location_payload.get("latitude") is None else float(location_payload["latitude"]),
                    longitude=None if location_payload.get("longitude") is None else float(location_payload["longitude"]),
                ),
                weather_units=str(values.get("weather_units", _DEFAULT_SETTINGS.weather_units)),
                weather_position=str(values.get("weather_position", _DEFAULT_SETTINGS.weather_position)),
                weather_refresh_minutes=int(values.get("weather_refresh_minutes", _DEFAULT_SETTINGS.weather_refresh_minutes)),
                weather_show_precipitation=bool(
                    int(values.get("weather_show_precipitation", 1 if _DEFAULT_SETTINGS.weather_show_precipitation else 0))
                ),
                weather_show_humidity=bool(int(values.get("weather_show_humidity", 1 if _DEFAULT_SETTINGS.weather_show_humidity else 0))),
                weather_show_wind=bool(int(values.get("weather_show_wind", 1 if _DEFAULT_SETTINGS.weather_show_wind else 0))),
                weather_alerts_enabled=bool(int(values.get("weather_alerts_enabled", 1 if _DEFAULT_SETTINGS.weather_alerts_enabled else 0))),
                weather_alert_fullscreen_enabled=bool(
                    int(values.get("weather_alert_fullscreen_enabled", 1 if _DEFAULT_SETTINGS.weather_alert_fullscreen_enabled else 0))
                ),
                weather_alert_minimum_severity=str(
                    values.get("weather_alert_minimum_severity", _DEFAULT_SETTINGS.weather_alert_minimum_severity)
                ),
                weather_alert_repeat_enabled=bool(
                    int(values.get("weather_alert_repeat_enabled", 1 if _DEFAULT_SETTINGS.weather_alert_repeat_enabled else 0))
                ),
                weather_alert_repeat_interval_minutes=int(
                    values.get("weather_alert_repeat_interval_minutes", _DEFAULT_SETTINGS.weather_alert_repeat_interval_minutes)
                ),
                weather_alert_repeat_display_seconds=int(
                    values.get("weather_alert_repeat_display_seconds", _DEFAULT_SETTINGS.weather_alert_repeat_display_seconds)
                ),
            )
        )

    def update_settings(self, settings: WeatherSettings) -> WeatherSettings:
        normalized = normalize_weather_settings(settings)
        now = utc_now()
        updates = {
            "weather_enabled": "1" if normalized.weather_enabled else "0",
            "weather_provider": normalized.weather_provider,
            "weather_location": json_dumps(
                {
                    "label": normalized.weather_location.label,
                    "latitude": normalized.weather_location.latitude,
                    "longitude": normalized.weather_location.longitude,
                }
            ),
            "weather_units": normalized.weather_units,
            "weather_position": normalized.weather_position,
            "weather_refresh_minutes": str(normalized.weather_refresh_minutes),
            "weather_show_precipitation": "1" if normalized.weather_show_precipitation else "0",
            "weather_show_humidity": "1" if normalized.weather_show_humidity else "0",
            "weather_show_wind": "1" if normalized.weather_show_wind else "0",
            "weather_alerts_enabled": "1" if normalized.weather_alerts_enabled else "0",
            "weather_alert_fullscreen_enabled": "1" if normalized.weather_alert_fullscreen_enabled else "0",
            "weather_alert_minimum_severity": normalized.weather_alert_minimum_severity,
            "weather_alert_repeat_enabled": "1" if normalized.weather_alert_repeat_enabled else "0",
            "weather_alert_repeat_interval_minutes": str(normalized.weather_alert_repeat_interval_minutes),
            "weather_alert_repeat_display_seconds": str(normalized.weather_alert_repeat_display_seconds),
        }
        with get_connection() as conn:
            if is_null_connection(conn):
                return normalized
            for key, value in updates.items():
                existing = conn.execute("select key from settings where key = ?", (key,)).fetchone()
                if existing is None:
                    conn.execute(
                        "insert into settings (key, value, updated_at) values (?, ?, ?)",
                        (key, value, now),
                    )
                else:
                    conn.execute(
                        "update settings set value = ?, updated_at = ? where key = ?",
                        (value, now, key),
                    )
        return normalized

    def get_provider_state(self, provider_name: str) -> WeatherProviderState | None:
        with get_connection() as conn:
            if is_null_connection(conn):
                return None
            cursor = conn.execute("select * from weather_provider_state where provider_name = ?", (provider_name,))
            row = row_to_dict(cursor, cursor.fetchone())
        return None if row is None else self._provider_state_from_row(row)

    def upsert_provider_state(self, state: WeatherProviderState) -> WeatherProviderState:
        with get_connection() as conn:
            if is_null_connection(conn):
                return state
            existing = conn.execute(
                "select provider_name from weather_provider_state where provider_name = ?",
                (state.provider_name,),
            ).fetchone()
            values = (
                state.provider_name,
                state.provider_display_name,
                state.status,
                bool_to_int(state.available),
                bool_to_int(state.configured),
                state.location_label,
                state.last_weather_refresh_at,
                state.last_alert_refresh_at,
                state.last_successful_weather_refresh_at,
                state.last_successful_alert_refresh_at,
                state.current_error,
                state.updated_at,
            )
            if existing is None:
                conn.execute(
                    """
                    insert into weather_provider_state (
                        provider_name, provider_display_name, status, available, configured, location_label,
                        last_weather_refresh_at, last_alert_refresh_at, last_successful_weather_refresh_at,
                        last_successful_alert_refresh_at, current_error, updated_at
                    ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    values,
                )
            else:
                conn.execute(
                    """
                    update weather_provider_state
                    set provider_display_name = ?, status = ?, available = ?, configured = ?, location_label = ?,
                        last_weather_refresh_at = ?, last_alert_refresh_at = ?, last_successful_weather_refresh_at = ?,
                        last_successful_alert_refresh_at = ?, current_error = ?, updated_at = ?
                    where provider_name = ?
                    """,
                    (
                        state.provider_display_name,
                        state.status,
                        bool_to_int(state.available),
                        bool_to_int(state.configured),
                        state.location_label,
                        state.last_weather_refresh_at,
                        state.last_alert_refresh_at,
                        state.last_successful_weather_refresh_at,
                        state.last_successful_alert_refresh_at,
                        state.current_error,
                        state.updated_at,
                        state.provider_name,
                    ),
                )
        return self.get_provider_state(state.provider_name) or state

    def get_current_conditions(self, provider_name: str, location_key: str) -> WeatherCurrentConditions | None:
        with get_connection() as conn:
            if is_null_connection(conn):
                return None
            cursor = conn.execute(
                "select * from weather_current_conditions where provider_name = ? and location_key = ?",
                (provider_name, location_key),
            )
            row = row_to_dict(cursor, cursor.fetchone())
        return None if row is None else self._conditions_from_row(row)

    def upsert_current_conditions(self, conditions: WeatherCurrentConditions) -> WeatherCurrentConditions:
        with get_connection() as conn:
            if is_null_connection(conn):
                return conditions
            existing = conn.execute(
                "select provider_name from weather_current_conditions where provider_name = ? and location_key = ?",
                (conditions.provider_name, conditions.location_key),
            ).fetchone()
            if existing is None:
                conn.execute(
                    """
                    insert into weather_current_conditions (
                        provider_name, provider_display_name, location_key, location_label, condition, icon_token,
                        temperature_c, humidity_percent, wind_speed_mph, wind_direction,
                        precipitation_probability_percent, observed_at, fetched_at, attribution, is_stale
                    ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        conditions.provider_name,
                        conditions.provider_display_name,
                        conditions.location_key,
                        conditions.location_label,
                        conditions.condition,
                        conditions.icon_token,
                        conditions.temperature_c,
                        conditions.humidity_percent,
                        conditions.wind_speed_mph,
                        conditions.wind_direction,
                        conditions.precipitation_probability_percent,
                        conditions.observed_at,
                        conditions.fetched_at,
                        conditions.attribution,
                        bool_to_int(conditions.is_stale),
                    ),
                )
            else:
                conn.execute(
                    """
                    update weather_current_conditions
                    set provider_display_name = ?, location_label = ?, condition = ?, icon_token = ?, temperature_c = ?,
                        humidity_percent = ?, wind_speed_mph = ?, wind_direction = ?,
                        precipitation_probability_percent = ?, observed_at = ?, fetched_at = ?, attribution = ?, is_stale = ?
                    where provider_name = ? and location_key = ?
                    """,
                    (
                        conditions.provider_display_name,
                        conditions.location_label,
                        conditions.condition,
                        conditions.icon_token,
                        conditions.temperature_c,
                        conditions.humidity_percent,
                        conditions.wind_speed_mph,
                        conditions.wind_direction,
                        conditions.precipitation_probability_percent,
                        conditions.observed_at,
                        conditions.fetched_at,
                        conditions.attribution,
                        bool_to_int(conditions.is_stale),
                        conditions.provider_name,
                        conditions.location_key,
                    ),
                )
        return self.get_current_conditions(conditions.provider_name, conditions.location_key) or conditions

    def replace_active_alerts(self, provider_name: str, location_key: str, alerts: list[WeatherAlert]) -> list[WeatherAlert]:
        with get_connection() as conn:
            if is_null_connection(conn):
                return alerts
            conn.execute(
                "delete from weather_alerts where provider_name = ? and location_key = ?",
                (provider_name, location_key),
            )
            for alert in alerts:
                conn.execute(
                    """
                    insert into weather_alerts (
                        id, provider_name, provider_display_name, location_key, source_alert_id, event, severity,
                        certainty, urgency, headline, description, instruction, area, status, issued_at,
                        effective_at, expires_at, ends_at, attribution, escalation_mode, display_priority,
                        event_priority, updated_at, fetched_at, is_active
                    ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        alert.id,
                        alert.provider_name,
                        alert.provider_display_name,
                        alert.location_key,
                        alert.source_alert_id,
                        alert.event,
                        alert.severity,
                        alert.certainty,
                        alert.urgency,
                        alert.headline,
                        alert.description,
                        alert.instruction,
                        alert.area,
                        alert.status,
                        alert.issued_at,
                        alert.effective_at,
                        alert.expires_at,
                        alert.ends_at,
                        alert.attribution,
                        alert.escalation_mode,
                        alert.display_priority,
                        alert.event_priority,
                        alert.updated_at,
                        alert.fetched_at,
                        bool_to_int(alert.is_active),
                    ),
                )
        return self.list_alerts(provider_name, location_key)

    def list_alerts(self, provider_name: str, location_key: str) -> list[WeatherAlert]:
        with get_connection() as conn:
            if is_null_connection(conn):
                return []
            cursor = conn.execute(
                """
                select * from weather_alerts
                where provider_name = ? and location_key = ?
                order by display_priority desc, updated_at desc, id desc
                """,
                (provider_name, location_key),
            )
            rows = rows_to_dicts(cursor, cursor.fetchall())
        return [self._alert_from_row(row) for row in rows]

    def create_refresh_run(self, refresh_run: WeatherRefreshRun) -> WeatherRefreshRun:
        def operation() -> WeatherRefreshRun:
            with get_connection() as conn:
                if is_null_connection(conn):
                    return refresh_run
                conn.execute(
                    """
                    insert into weather_refresh_runs (
                        id, provider_name, refresh_kind, trigger, status, message, error_message, started_at, completed_at
                    ) values (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        refresh_run.id,
                        refresh_run.provider_name,
                        refresh_run.refresh_kind,
                        refresh_run.trigger,
                        refresh_run.status,
                        refresh_run.message,
                        refresh_run.error_message,
                        refresh_run.started_at,
                        refresh_run.completed_at,
                    ),
                )
            return self.get_refresh_run(refresh_run.id) or refresh_run

        return self._with_refresh_run_storage_recovery(
            "create_refresh_run", operation
        )

    def update_refresh_run(self, refresh_run: WeatherRefreshRun) -> WeatherRefreshRun:
        def operation() -> WeatherRefreshRun:
            with get_connection() as conn:
                if is_null_connection(conn):
                    return refresh_run
                conn.execute(
                    """
                    update weather_refresh_runs
                    set provider_name = ?, refresh_kind = ?, trigger = ?, status = ?, message = ?, error_message = ?,
                        started_at = ?, completed_at = ?
                    where id = ?
                    """,
                    (
                        refresh_run.provider_name,
                        refresh_run.refresh_kind,
                        refresh_run.trigger,
                        refresh_run.status,
                        refresh_run.message,
                        refresh_run.error_message,
                        refresh_run.started_at,
                        refresh_run.completed_at,
                        refresh_run.id,
                    ),
                )
            return self.get_refresh_run(refresh_run.id) or refresh_run

        return self._with_refresh_run_storage_recovery(
            "update_refresh_run", operation
        )

    def get_refresh_run(self, refresh_run_id: str) -> WeatherRefreshRun | None:
        row = self._with_refresh_run_storage_recovery(
            "get_refresh_run",
            lambda: self._get_refresh_run_row(refresh_run_id),
        )
        return None if row is None else self._refresh_run_from_row(row)

    def list_refresh_runs(self, provider_name: str, *, limit: int = 10) -> list[WeatherRefreshRun]:
        rows = self._with_refresh_run_storage_recovery(
            "list_refresh_runs",
            lambda: self._list_refresh_run_rows(provider_name, limit),
        )
        return [self._refresh_run_from_row(row) for row in rows]

    def _get_refresh_run_row(self, refresh_run_id: str) -> dict[str, object] | None:
        with get_connection() as conn:
            if is_null_connection(conn):
                return None
            cursor = conn.execute(
                "select * from weather_refresh_runs where id = ?",
                (refresh_run_id,),
            )
            return row_to_dict(cursor, cursor.fetchone())

    def _list_refresh_run_rows(
        self, provider_name: str, limit: int
    ) -> list[dict[str, object]]:
        with get_connection() as conn:
            if is_null_connection(conn):
                return []
            cursor = conn.execute(
                """
                select * from weather_refresh_runs
                where provider_name = ?
                order by started_at desc, id desc
                limit ?
                """,
                (provider_name, max(1, limit)),
            )
            return rows_to_dicts(cursor, cursor.fetchall())

    def _with_refresh_run_storage_recovery(
        self, operation_name: str, operation: Callable[[], _T]
    ) -> _T:
        try:
            return operation()
        except Exception as exc:
            if not is_recoverable_database_error(exc):
                raise

            LOGGER.warning(
                "weather_refresh_runs_storage_corrupt_repairing",
                operation=operation_name,
                exc_info=exc,
            )
            self._repair_refresh_run_storage()
            LOGGER.warning(
                "weather_refresh_runs_storage_rebuilt",
                operation=operation_name,
            )
            return operation()

    def _repair_refresh_run_storage(self) -> None:
        # Refresh-run history is operational metadata; if its pages/indexes are
        # corrupt we can rebuild just this table instead of quarantining the
        # entire library metadata database.
        with exclusive_database_access():
            reset_connection_state()
            with get_connection() as conn:
                if is_null_connection(conn):
                    return
                for index_name in _REFRESH_RUNS_INDEXES:
                    conn.execute(f"drop index if exists {index_name}")
                conn.execute(f"drop table if exists {_REFRESH_RUNS_TABLE}")
                conn.execute(TABLE_STATEMENTS[_REFRESH_RUNS_TABLE])
                for index_name in _REFRESH_RUNS_INDEXES:
                    conn.execute(INDEX_STATEMENTS[index_name])
            reset_connection_state()

    @staticmethod
    def _provider_state_from_row(row: dict[str, object]) -> WeatherProviderState:
        return WeatherProviderState(
            provider_name=str(row["provider_name"]),
            provider_display_name=str(row["provider_display_name"]),
            status=str(row["status"]),
            available=int_to_bool(row["available"]),
            configured=int_to_bool(row["configured"]),
            location_label=str(row["location_label"] or ""),
            last_weather_refresh_at=None if row["last_weather_refresh_at"] is None else str(row["last_weather_refresh_at"]),
            last_alert_refresh_at=None if row["last_alert_refresh_at"] is None else str(row["last_alert_refresh_at"]),
            last_successful_weather_refresh_at=(
                None if row["last_successful_weather_refresh_at"] is None else str(row["last_successful_weather_refresh_at"])
            ),
            last_successful_alert_refresh_at=(
                None if row["last_successful_alert_refresh_at"] is None else str(row["last_successful_alert_refresh_at"])
            ),
            current_error=str(row["current_error"] or ""),
            updated_at=str(row["updated_at"]),
        )

    @staticmethod
    def _conditions_from_row(row: dict[str, object]) -> WeatherCurrentConditions:
        return WeatherCurrentConditions(
            provider_name=str(row["provider_name"]),
            provider_display_name=str(row["provider_display_name"]),
            location_key=str(row["location_key"]),
            location_label=str(row["location_label"]),
            condition=str(row["condition"]),
            icon_token=str(row["icon_token"]),
            temperature_c=None if row["temperature_c"] is None else float(row["temperature_c"]),
            humidity_percent=None if row["humidity_percent"] is None else int(row["humidity_percent"]),
            wind_speed_mph=None if row["wind_speed_mph"] is None else float(row["wind_speed_mph"]),
            wind_direction=None if row["wind_direction"] is None else str(row["wind_direction"]),
            precipitation_probability_percent=(
                None if row["precipitation_probability_percent"] is None else int(row["precipitation_probability_percent"])
            ),
            observed_at=None if row["observed_at"] is None else str(row["observed_at"]),
            fetched_at=str(row["fetched_at"]),
            attribution=str(row["attribution"] or ""),
            is_stale=int_to_bool(row["is_stale"]),
        )

    @staticmethod
    def _alert_from_row(row: dict[str, object]) -> WeatherAlert:
        return WeatherAlert(
            id=str(row["id"]),
            provider_name=str(row["provider_name"]),
            provider_display_name=str(row["provider_display_name"]),
            location_key=str(row["location_key"]),
            source_alert_id=str(row["source_alert_id"]),
            event=str(row["event"]),
            severity=str(row["severity"]),  # type: ignore[arg-type]
            certainty=str(row["certainty"]),
            urgency=str(row["urgency"]),
            headline=str(row["headline"]),
            description=str(row["description"] or ""),
            instruction=str(row["instruction"] or ""),
            area=str(row["area"]),
            status=str(row["status"]),
            issued_at=None if row["issued_at"] is None else str(row["issued_at"]),
            effective_at=None if row["effective_at"] is None else str(row["effective_at"]),
            expires_at=None if row["expires_at"] is None else str(row["expires_at"]),
            ends_at=None if row["ends_at"] is None else str(row["ends_at"]),
            attribution=str(row["attribution"] or ""),
            escalation_mode=str(row["escalation_mode"]),  # type: ignore[arg-type]
            display_priority=int(row["display_priority"]),
            event_priority=int(row["event_priority"]),
            updated_at=str(row["updated_at"]),
            fetched_at=str(row["fetched_at"]),
            is_active=int_to_bool(row["is_active"]),
        )

    @staticmethod
    def _refresh_run_from_row(row: dict[str, object]) -> WeatherRefreshRun:
        return WeatherRefreshRun(
            id=str(row["id"]),
            provider_name=str(row["provider_name"]),
            refresh_kind=str(row["refresh_kind"]),
            trigger=str(row["trigger"]),
            status=str(row["status"]),
            message=str(row["message"] or ""),
            error_message=str(row["error_message"] or ""),
            started_at=str(row["started_at"]),
            completed_at=None if row["completed_at"] is None else str(row["completed_at"]),
        )

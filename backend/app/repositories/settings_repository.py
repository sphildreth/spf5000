from __future__ import annotations

from app.db.bootstrap import DEFAULT_COLLECTION_ID, DEFAULT_DISPLAY_PROFILE_ID
from app.db.connection import get_connection, is_null_connection
from app.models.settings import FrameSettings
from app.models.sleep_schedule import SleepSchedule, normalize_sleep_schedule
from app.repositories.base import utc_now

_SLEEP_SCHEDULE_KEYS = (
    "sleep_schedule_enabled",
    "sleep_start_local_time",
    "sleep_end_local_time",
    "display_timezone",
)
_SLEEP_SCHEDULE_DEFAULTS = SleepSchedule()


class SettingsRepository:
    def get_settings(self) -> FrameSettings:
        defaults = FrameSettings(
            selected_collection_id=DEFAULT_COLLECTION_ID,
            active_display_profile_id=DEFAULT_DISPLAY_PROFILE_ID,
        )
        with get_connection() as conn:
            if is_null_connection(conn):
                return defaults
            cursor = conn.execute(
                "select key, value from settings where key in (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    "frame_name",
                    "display_variant_width",
                    "display_variant_height",
                    "thumbnail_max_size",
                    "slideshow_interval_seconds",
                    "transition_mode",
                    "transition_duration_ms",
                    "fit_mode",
                    "shuffle_enabled",
                    "shuffle_bag_enabled",
                    "selected_collection_id",
                    "active_display_profile_id",
                    "background_fill_mode",
                ),
            )
            rows = cursor.fetchall()
            values = {key: value for key, value in rows}
            return FrameSettings(
                frame_name=str(values.get("frame_name", defaults.frame_name)),
                display_variant_width=int(values.get("display_variant_width", defaults.display_variant_width)),
                display_variant_height=int(values.get("display_variant_height", defaults.display_variant_height)),
                thumbnail_max_size=int(values.get("thumbnail_max_size", defaults.thumbnail_max_size)),
                slideshow_interval_seconds=int(values.get("slideshow_interval_seconds", defaults.slideshow_interval_seconds)),
                transition_mode=str(values.get("transition_mode", defaults.transition_mode)),
                transition_duration_ms=int(values.get("transition_duration_ms", defaults.transition_duration_ms)),
                fit_mode=str(values.get("fit_mode", defaults.fit_mode)),
                shuffle_enabled=bool(int(values.get("shuffle_enabled", 1 if defaults.shuffle_enabled else 0))),
                shuffle_bag_enabled=bool(int(values.get("shuffle_bag_enabled", 1 if defaults.shuffle_bag_enabled else 0))),
                selected_collection_id=str(values.get("selected_collection_id", defaults.selected_collection_id)),
                active_display_profile_id=str(values.get("active_display_profile_id", defaults.active_display_profile_id)),
                background_fill_mode=str(values.get("background_fill_mode", defaults.background_fill_mode)),
            )

    def update_settings(self, frame_settings: FrameSettings) -> FrameSettings:
        with get_connection() as conn:
            if is_null_connection(conn):
                return frame_settings
            now = utc_now()
            updates = {
                "frame_name": frame_settings.frame_name,
                "display_variant_width": str(frame_settings.display_variant_width),
                "display_variant_height": str(frame_settings.display_variant_height),
                "thumbnail_max_size": str(frame_settings.thumbnail_max_size),
                "slideshow_interval_seconds": str(frame_settings.slideshow_interval_seconds),
                "transition_mode": frame_settings.transition_mode,
                "transition_duration_ms": str(frame_settings.transition_duration_ms),
                "fit_mode": frame_settings.fit_mode,
                "shuffle_enabled": "1" if frame_settings.shuffle_enabled else "0",
                "shuffle_bag_enabled": "1" if frame_settings.shuffle_bag_enabled else "0",
                "selected_collection_id": frame_settings.selected_collection_id,
                "active_display_profile_id": frame_settings.active_display_profile_id,
                "background_fill_mode": frame_settings.background_fill_mode,
            }
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
        return frame_settings

    def get_sleep_schedule(self) -> SleepSchedule:
        d = _SLEEP_SCHEDULE_DEFAULTS
        with get_connection() as conn:
            if is_null_connection(conn):
                return d
            cursor = conn.execute(
                "select key, value from settings where key in (?, ?, ?, ?)",
                _SLEEP_SCHEDULE_KEYS,
            )
            rows = cursor.fetchall()
            values = {key: value for key, value in rows}
            return normalize_sleep_schedule(
                SleepSchedule(
                    sleep_schedule_enabled=bool(int(values.get("sleep_schedule_enabled", "0"))),
                    sleep_start_local_time=str(values.get("sleep_start_local_time", d.sleep_start_local_time)),
                    sleep_end_local_time=str(values.get("sleep_end_local_time", d.sleep_end_local_time)),
                    display_timezone=values.get("display_timezone"),
                )
            )

    def update_sleep_schedule(self, schedule: SleepSchedule) -> SleepSchedule:
        normalized = normalize_sleep_schedule(schedule)
        with get_connection() as conn:
            if is_null_connection(conn):
                return normalized
            now = utc_now()
            updates = {
                "sleep_schedule_enabled": "1" if normalized.sleep_schedule_enabled else "0",
                "sleep_start_local_time": normalized.sleep_start_local_time,
                "sleep_end_local_time": normalized.sleep_end_local_time,
                "display_timezone": normalized.display_timezone or "",
            }
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

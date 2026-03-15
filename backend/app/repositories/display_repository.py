from __future__ import annotations

from app.db.connection import get_connection, is_null_connection
from app.models.display import DisplayProfile
from app.repositories.base import bool_to_int, int_to_bool, row_to_dict, utc_now


class DisplayRepository:
    def get_default_profile(self) -> DisplayProfile | None:
        with get_connection() as conn:
            if is_null_connection(conn):
                return None
            cursor = conn.execute("select * from display_profiles where is_default = 1 limit 1")
            row = row_to_dict(cursor, cursor.fetchone())
            return None if row is None else self._to_model(row)

    def update_profile(self, profile: DisplayProfile) -> DisplayProfile:
        with get_connection() as conn:
            if is_null_connection(conn):
                return profile
            now = utc_now()
            conn.execute(
                """
                update display_profiles
                set name = ?, selected_collection_id = ?, slideshow_interval_seconds = ?, transition_mode = ?,
                    transition_duration_ms = ?, fit_mode = ?, shuffle_enabled = ?, idle_message = ?,
                    refresh_interval_seconds = ?, updated_at = ?
                where id = ?
                """,
                (
                    profile.name,
                    profile.selected_collection_id,
                    profile.slideshow_interval_seconds,
                    profile.transition_mode,
                    profile.transition_duration_ms,
                    profile.fit_mode,
                    bool_to_int(profile.shuffle_enabled),
                    profile.idle_message,
                    profile.refresh_interval_seconds,
                    now,
                    profile.id,
                ),
            )
        return self.get_default_profile() or profile

    @staticmethod
    def _to_model(row: dict[str, object]) -> DisplayProfile:
        return DisplayProfile(
            id=str(row["id"]),
            name=str(row["name"]),
            selected_collection_id=None if row["selected_collection_id"] is None else str(row["selected_collection_id"]),
            slideshow_interval_seconds=int(row["slideshow_interval_seconds"]),
            transition_mode=str(row["transition_mode"]),
            transition_duration_ms=int(row["transition_duration_ms"]),
            fit_mode=str(row["fit_mode"]),
            shuffle_enabled=int_to_bool(row["shuffle_enabled"]),
            idle_message=str(row["idle_message"] or ""),
            refresh_interval_seconds=int(row["refresh_interval_seconds"] or 60),
            is_default=int_to_bool(row["is_default"]),
            created_at=str(row["created_at"]),
            updated_at=str(row["updated_at"]),
        )

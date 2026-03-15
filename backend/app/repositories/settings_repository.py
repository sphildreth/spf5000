from __future__ import annotations

from app.db.connection import get_connection
from app.models.settings import FrameSettings


class SettingsRepository:
    def get_settings(self) -> FrameSettings:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("select 1")
            return FrameSettings()

    def update_settings(self, settings: FrameSettings) -> FrameSettings:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("select 1")
            return settings

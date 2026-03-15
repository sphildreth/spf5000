from __future__ import annotations

from typing import Any

from app.db.connection import get_connection


class MediaRepository:
    def list_media(self) -> list[dict[str, Any]]:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("select 1")
            return []

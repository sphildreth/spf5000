from __future__ import annotations

from app.db.connection import get_connection, is_null_connection
from app.models.source import Source
from app.repositories.base import bool_to_int, int_to_bool, row_to_dict, rows_to_dicts, utc_now


class SourceRepository:
    def list_sources(self) -> list[Source]:
        with get_connection() as conn:
            if is_null_connection(conn):
                return []
            cursor = conn.execute(
                """
                select
                    s.id,
                    s.name,
                    s.provider_type,
                    s.import_path,
                    s.enabled,
                    s.created_at,
                    s.updated_at,
                    s.last_scan_at,
                    s.last_import_at,
                    count(a.id) as asset_count
                from sources s
                left join assets a on a.source_id = s.id and a.is_active = 1
                group by s.id, s.name, s.provider_type, s.import_path, s.enabled, s.created_at, s.updated_at, s.last_scan_at, s.last_import_at
                order by s.name asc
                """
            )
            return [self._to_model(row) for row in rows_to_dicts(cursor, cursor.fetchall())]

    def get_source(self, source_id: str) -> Source | None:
        with get_connection() as conn:
            if is_null_connection(conn):
                return None
            cursor = conn.execute(
                """
                select
                    s.id,
                    s.name,
                    s.provider_type,
                    s.import_path,
                    s.enabled,
                    s.created_at,
                    s.updated_at,
                    s.last_scan_at,
                    s.last_import_at,
                    count(a.id) as asset_count
                from sources s
                left join assets a on a.source_id = s.id and a.is_active = 1
                where s.id = ?
                group by s.id, s.name, s.provider_type, s.import_path, s.enabled, s.created_at, s.updated_at, s.last_scan_at, s.last_import_at
                """,
                (source_id,),
            )
            row = row_to_dict(cursor, cursor.fetchone())
            return None if row is None else self._to_model(row)

    def update_source(self, source: Source) -> Source:
        with get_connection() as conn:
            if is_null_connection(conn):
                return source
            now = utc_now()
            conn.execute(
                """
                update sources
                set name = ?, import_path = ?, enabled = ?, updated_at = ?
                where id = ?
                """,
                (source.name, source.import_path, bool_to_int(source.enabled), now, source.id),
            )
        return self.get_source(source.id) or source

    def touch_last_scan(self, source_id: str, timestamp: str) -> None:
        with get_connection() as conn:
            if is_null_connection(conn):
                return
            conn.execute(
                "update sources set last_scan_at = ?, updated_at = ? where id = ?",
                (timestamp, timestamp, source_id),
            )

    def touch_last_import(self, source_id: str, timestamp: str) -> None:
        with get_connection() as conn:
            if is_null_connection(conn):
                return
            conn.execute(
                "update sources set last_import_at = ?, updated_at = ? where id = ?",
                (timestamp, timestamp, source_id),
            )

    @staticmethod
    def _to_model(row: dict[str, object]) -> Source:
        return Source(
            id=str(row["id"]),
            name=str(row["name"]),
            provider_type=str(row["provider_type"]),
            import_path=str(row["import_path"]),
            enabled=int_to_bool(row["enabled"]),
            created_at=str(row["created_at"]),
            updated_at=str(row["updated_at"]),
            last_scan_at=None if row["last_scan_at"] is None else str(row["last_scan_at"]),
            last_import_at=None if row["last_import_at"] is None else str(row["last_import_at"]),
            asset_count=int(row["asset_count"] or 0),
        )

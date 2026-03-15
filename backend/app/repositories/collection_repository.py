from __future__ import annotations

from app.db.connection import get_connection, is_null_connection
from app.models.collection import Collection
from app.repositories.base import bool_to_int, int_to_bool, row_to_dict, rows_to_dicts, utc_now


class CollectionRepository:
    def list_collections(self) -> list[Collection]:
        with get_connection() as conn:
            if is_null_connection(conn):
                return []
            cursor = conn.execute(
                """
                select
                    c.id,
                    c.name,
                    c.description,
                    c.source_id,
                    c.is_default,
                    c.is_active,
                    c.created_at,
                    c.updated_at,
                    count(ca.asset_id) as asset_count
                from collections c
                left join collection_assets ca on ca.collection_id = c.id
                group by c.id, c.name, c.description, c.source_id, c.is_default, c.is_active, c.created_at, c.updated_at
                order by c.is_default desc, c.name asc
                """
            )
            return [self._to_model(row) for row in rows_to_dicts(cursor, cursor.fetchall())]

    def get_collection(self, collection_id: str) -> Collection | None:
        with get_connection() as conn:
            if is_null_connection(conn):
                return None
            cursor = conn.execute(
                """
                select
                    c.id,
                    c.name,
                    c.description,
                    c.source_id,
                    c.is_default,
                    c.is_active,
                    c.created_at,
                    c.updated_at,
                    count(ca.asset_id) as asset_count
                from collections c
                left join collection_assets ca on ca.collection_id = c.id
                where c.id = ?
                group by c.id, c.name, c.description, c.source_id, c.is_default, c.is_active, c.created_at, c.updated_at
                """,
                (collection_id,),
            )
            row = row_to_dict(cursor, cursor.fetchone())
            return None if row is None else self._to_model(row)

    def create_collection(self, collection: Collection) -> Collection:
        with get_connection() as conn:
            if is_null_connection(conn):
                return collection
            conn.execute(
                """
                insert into collections (
                    id, name, description, source_id, is_default, is_active, created_at, updated_at
                ) values (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    collection.id,
                    collection.name,
                    collection.description,
                    collection.source_id,
                    bool_to_int(collection.is_default),
                    bool_to_int(collection.is_active),
                    collection.created_at,
                    collection.updated_at,
                ),
            )
        return self.get_collection(collection.id) or collection

    def update_collection(self, collection: Collection) -> Collection:
        with get_connection() as conn:
            if is_null_connection(conn):
                return collection
            now = utc_now()
            conn.execute(
                """
                update collections
                set name = ?, description = ?, source_id = ?, is_active = ?, updated_at = ?
                where id = ?
                """,
                (
                    collection.name,
                    collection.description,
                    collection.source_id,
                    bool_to_int(collection.is_active),
                    now,
                    collection.id,
                ),
            )
        return self.get_collection(collection.id) or collection

    @staticmethod
    def _to_model(row: dict[str, object]) -> Collection:
        return Collection(
            id=str(row["id"]),
            name=str(row["name"]),
            description=str(row["description"]),
            source_id=None if row["source_id"] is None else str(row["source_id"]),
            is_default=int_to_bool(row["is_default"]),
            is_active=int_to_bool(row["is_active"]),
            created_at=str(row["created_at"]),
            updated_at=str(row["updated_at"]),
            asset_count=int(row["asset_count"] or 0),
        )

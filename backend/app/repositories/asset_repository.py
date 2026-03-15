from __future__ import annotations

from collections import defaultdict

from app.db.connection import get_connection, is_null_connection
from app.models.asset import Asset, AssetVariant
from app.repositories.base import bool_to_int, int_to_bool, row_to_dict, rows_to_dicts, utc_now


class AssetRepository:
    def list_assets(self, collection_id: str | None = None) -> list[Asset]:
        with get_connection() as conn:
            if is_null_connection(conn):
                return []
            if collection_id:
                cursor = conn.execute(
                    """
                    select a.*
                    from assets a
                    join collection_assets ca on ca.asset_id = a.id
                    where ca.collection_id = ? and a.is_active = 1
                    order by lower(a.filename) asc, a.imported_at asc, a.id asc
                    """,
                    (collection_id,),
                )
            else:
                cursor = conn.execute(
                    """
                    select a.*
                    from assets a
                    where a.is_active = 1
                    order by a.imported_at desc, a.id desc
                    """
                )
            assets = [self._to_model(row) for row in rows_to_dicts(cursor, cursor.fetchall())]
        return self._attach_related(assets)

    def get_asset(self, asset_id: str) -> Asset | None:
        with get_connection() as conn:
            if is_null_connection(conn):
                return None
            cursor = conn.execute("select * from assets where id = ?", (asset_id,))
            row = row_to_dict(cursor, cursor.fetchone())
        if row is None:
            return None
        return self._attach_related([self._to_model(row)])[0]

    def find_by_checksum(self, checksum_sha256: str) -> Asset | None:
        with get_connection() as conn:
            if is_null_connection(conn):
                return None
            cursor = conn.execute("select * from assets where checksum_sha256 = ?", (checksum_sha256,))
            row = row_to_dict(cursor, cursor.fetchone())
        if row is None:
            return None
        return self._attach_related([self._to_model(row)])[0]

    def create_asset(self, asset: Asset) -> Asset:
        with get_connection() as conn:
            if is_null_connection(conn):
                return asset
            conn.execute(
                """
                insert into assets (
                    id, source_id, checksum_sha256, filename, original_filename, original_extension,
                    mime_type, width, height, size_bytes, imported_from_path, local_original_path,
                    metadata_json, created_at, updated_at, imported_at, is_active
                ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    asset.id,
                    asset.source_id,
                    asset.checksum_sha256,
                    asset.filename,
                    asset.original_filename,
                    asset.original_extension,
                    asset.mime_type,
                    asset.width,
                    asset.height,
                    asset.size_bytes,
                    asset.imported_from_path,
                    asset.local_original_path,
                    asset.metadata_json,
                    asset.created_at,
                    asset.updated_at,
                    asset.imported_at,
                    bool_to_int(asset.is_active),
                ),
            )
            for variant in asset.variants:
                conn.execute(
                    """
                    insert into asset_variants (
                        id, asset_id, kind, local_path, mime_type, width, height, size_bytes, created_at
                    ) values (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        variant.id,
                        variant.asset_id,
                        variant.kind,
                        variant.local_path,
                        variant.mime_type,
                        variant.width,
                        variant.height,
                        variant.size_bytes,
                        variant.created_at,
                    ),
                )
            for index, collection_id in enumerate(asset.collection_ids):
                conn.execute(
                    """
                    insert or ignore into collection_assets (collection_id, asset_id, sort_order, added_at)
                    values (?, ?, ?, ?)
                    """,
                    (collection_id, asset.id, index, asset.created_at),
                )
        return self.get_asset(asset.id) or asset

    def add_asset_to_collection(self, asset_id: str, collection_id: str) -> None:
        with get_connection() as conn:
            if is_null_connection(conn):
                return
            existing = conn.execute(
                "select asset_id from collection_assets where collection_id = ? and asset_id = ?",
                (collection_id, asset_id),
            ).fetchone()
            if existing is None:
                sort_order = int(
                    conn.execute(
                        "select count(*) from collection_assets where collection_id = ?",
                        (collection_id,),
                    ).fetchone()[0]
                )
                conn.execute(
                    "insert into collection_assets (collection_id, asset_id, sort_order, added_at) values (?, ?, ?, ?)",
                    (collection_id, asset_id, sort_order, utc_now()),
                )

    def get_variant(self, asset_id: str, kind: str) -> AssetVariant | None:
        with get_connection() as conn:
            if is_null_connection(conn):
                return None
            cursor = conn.execute(
                "select * from asset_variants where asset_id = ? and kind = ?",
                (asset_id, kind),
            )
            row = row_to_dict(cursor, cursor.fetchone())
            return None if row is None else self._variant_from_row(row)

    def count_assets(self) -> int:
        with get_connection() as conn:
            if is_null_connection(conn):
                return 0
            cursor = conn.execute("select count(*) from assets where is_active = 1")
            return int(cursor.fetchone()[0])

    def _attach_related(self, assets: list[Asset]) -> list[Asset]:
        if not assets:
            return assets
        asset_ids = [asset.id for asset in assets]
        placeholders = ", ".join("?" for _ in asset_ids)
        with get_connection() as conn:
            if is_null_connection(conn):
                return assets
            variants_cursor = conn.execute(
                f"select * from asset_variants where asset_id in ({placeholders}) order by kind asc",
                tuple(asset_ids),
            )
            collection_cursor = conn.execute(
                f"select collection_id, asset_id from collection_assets where asset_id in ({placeholders}) order by sort_order asc",
                tuple(asset_ids),
            )
            variants_map: dict[str, list[AssetVariant]] = defaultdict(list)
            for row in rows_to_dicts(variants_cursor, variants_cursor.fetchall()):
                variant = self._variant_from_row(row)
                variants_map[variant.asset_id].append(variant)
            collections_map: dict[str, list[str]] = defaultdict(list)
            for collection_id, asset_id in collection_cursor.fetchall():
                collections_map[str(asset_id)].append(str(collection_id))

        for asset in assets:
            asset.variants = variants_map.get(asset.id, [])
            asset.collection_ids = collections_map.get(asset.id, [])
        return assets

    @staticmethod
    def _to_model(row: dict[str, object]) -> Asset:
        return Asset(
            id=str(row["id"]),
            source_id=str(row["source_id"]),
            checksum_sha256=str(row["checksum_sha256"]),
            filename=str(row["filename"]),
            original_filename=str(row["original_filename"]),
            original_extension=str(row["original_extension"]),
            mime_type=str(row["mime_type"]),
            width=int(row["width"]),
            height=int(row["height"]),
            size_bytes=int(row["size_bytes"]),
            imported_from_path=str(row["imported_from_path"]),
            local_original_path=str(row["local_original_path"]),
            metadata_json=str(row["metadata_json"]),
            created_at=str(row["created_at"]),
            updated_at=str(row["updated_at"]),
            imported_at=str(row["imported_at"]),
            is_active=int_to_bool(row["is_active"]),
        )

    @staticmethod
    def _variant_from_row(row: dict[str, object]) -> AssetVariant:
        return AssetVariant(
            id=str(row["id"]),
            asset_id=str(row["asset_id"]),
            kind=str(row["kind"]),
            local_path=str(row["local_path"]),
            mime_type=str(row["mime_type"]),
            width=int(row["width"]),
            height=int(row["height"]),
            size_bytes=int(row["size_bytes"]),
            created_at=str(row["created_at"]),
        )

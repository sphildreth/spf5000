from __future__ import annotations

from collections import defaultdict
from typing import Iterable

from app.db.connection import get_connection, is_null_connection
from app.providers.google_photos.models import (
    GooglePhotosAccount,
    GooglePhotosAuthFlow,
    GooglePhotosDevice,
    GooglePhotosMediaSource,
    GooglePhotosProviderAsset,
    GooglePhotosSyncRun,
)
from app.repositories.base import bool_to_int, int_to_bool, json_dumps, json_loads, row_to_dict, rows_to_dicts, utc_now

_PROVIDER_TYPE = "google_photos"
_SUCCESSFUL_SYNC_STATUSES = {"completed", "completed_with_warnings"}


class GooglePhotosRepository:
    def get_pending_auth_flow(self, source_id: str) -> GooglePhotosAuthFlow | None:
        with get_connection() as conn:
            if is_null_connection(conn):
                return None
            cursor = conn.execute(
                """
                select *
                from provider_auth_flows
                where provider_type = ? and source_id = ? and status = 'pending'
                order by created_at desc, id desc
                limit 1
                """,
                (_PROVIDER_TYPE, source_id),
            )
            row = row_to_dict(cursor, cursor.fetchone())
            return None if row is None else self._auth_flow_from_row(row)

    def cancel_pending_auth_flows(self, source_id: str) -> None:
        with get_connection() as conn:
            if is_null_connection(conn):
                return
            now = utc_now()
            conn.execute(
                """
                update provider_auth_flows
                set status = 'canceled', updated_at = ?, completed_at = ?
                where provider_type = ? and source_id = ? and status = 'pending'
                """,
                (now, now, _PROVIDER_TYPE, source_id),
            )

    def create_auth_flow(self, flow: GooglePhotosAuthFlow) -> GooglePhotosAuthFlow:
        with get_connection() as conn:
            if is_null_connection(conn):
                return flow
            conn.execute(
                """
                insert into provider_auth_flows (
                    id, provider_type, source_id, request_id, device_code, user_code,
                    verification_uri, interval_seconds, expires_at, status, error_message,
                    device_display_name, created_at, updated_at, completed_at
                ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    flow.id,
                    flow.provider_type,
                    flow.source_id,
                    flow.request_id,
                    flow.device_code,
                    flow.user_code,
                    flow.verification_uri,
                    flow.interval_seconds,
                    flow.expires_at,
                    flow.status,
                    flow.error_message,
                    flow.device_display_name,
                    flow.created_at,
                    flow.updated_at,
                    flow.completed_at,
                ),
            )
        return self.get_pending_auth_flow(flow.source_id) or flow

    def update_auth_flow(self, flow: GooglePhotosAuthFlow) -> GooglePhotosAuthFlow:
        with get_connection() as conn:
            if is_null_connection(conn):
                return flow
            conn.execute(
                """
                update provider_auth_flows
                set status = ?, error_message = ?, updated_at = ?, completed_at = ?
                where id = ?
                """,
                (flow.status, flow.error_message, flow.updated_at, flow.completed_at, flow.id),
            )
        return self.get_auth_flow(flow.id) or flow

    def get_auth_flow(self, flow_id: str) -> GooglePhotosAuthFlow | None:
        with get_connection() as conn:
            if is_null_connection(conn):
                return None
            cursor = conn.execute("select * from provider_auth_flows where id = ?", (flow_id,))
            row = row_to_dict(cursor, cursor.fetchone())
            return None if row is None else self._auth_flow_from_row(row)

    def get_account(self, source_id: str) -> GooglePhotosAccount | None:
        with get_connection() as conn:
            if is_null_connection(conn):
                return None
            cursor = conn.execute(
                "select * from provider_accounts where provider_type = ? and source_id = ? limit 1",
                (_PROVIDER_TYPE, source_id),
            )
            row = row_to_dict(cursor, cursor.fetchone())
            return None if row is None else self._account_from_row(row)

    def upsert_account(self, account: GooglePhotosAccount) -> GooglePhotosAccount:
        with get_connection() as conn:
            if is_null_connection(conn):
                return account
            existing = conn.execute(
                "select id from provider_accounts where provider_type = ? and source_id = ? limit 1",
                (_PROVIDER_TYPE, account.source_id),
            ).fetchone()
            if existing is None:
                conn.execute(
                    """
                    insert into provider_accounts (
                        id, provider_type, source_id, connection_state, account_subject,
                        account_email, account_display_name, account_picture_url,
                        access_token, refresh_token, scope, access_token_expires_at,
                        connected_at, disconnected_at, last_error, created_at, updated_at
                    ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        account.id,
                        account.provider_type,
                        account.source_id,
                        account.connection_state,
                        account.account_subject,
                        account.account_email,
                        account.account_display_name,
                        account.account_picture_url,
                        account.access_token,
                        account.refresh_token,
                        account.scope,
                        account.access_token_expires_at,
                        account.connected_at,
                        account.disconnected_at,
                        account.last_error,
                        account.created_at,
                        account.updated_at,
                    ),
                )
            else:
                conn.execute(
                    """
                    update provider_accounts
                    set connection_state = ?, account_subject = ?, account_email = ?,
                        account_display_name = ?, account_picture_url = ?, access_token = ?,
                        refresh_token = ?, scope = ?, access_token_expires_at = ?, connected_at = ?,
                        disconnected_at = ?, last_error = ?, updated_at = ?
                    where provider_type = ? and source_id = ?
                    """,
                    (
                        account.connection_state,
                        account.account_subject,
                        account.account_email,
                        account.account_display_name,
                        account.account_picture_url,
                        account.access_token,
                        account.refresh_token,
                        account.scope,
                        account.access_token_expires_at,
                        account.connected_at,
                        account.disconnected_at,
                        account.last_error,
                        account.updated_at,
                        _PROVIDER_TYPE,
                        account.source_id,
                    ),
                )
        return self.get_account(account.source_id) or account

    def get_device(self, source_id: str) -> GooglePhotosDevice | None:
        with get_connection() as conn:
            if is_null_connection(conn):
                return None
            cursor = conn.execute(
                "select * from provider_devices where provider_type = ? and source_id = ? limit 1",
                (_PROVIDER_TYPE, source_id),
            )
            row = row_to_dict(cursor, cursor.fetchone())
            return None if row is None else self._device_from_row(row)

    def upsert_device(self, device: GooglePhotosDevice) -> GooglePhotosDevice:
        with get_connection() as conn:
            if is_null_connection(conn):
                return device
            existing = conn.execute(
                "select id from provider_devices where provider_type = ? and source_id = ? limit 1",
                (_PROVIDER_TYPE, device.source_id),
            ).fetchone()
            if existing is None:
                conn.execute(
                    """
                    insert into provider_devices (
                        id, provider_account_id, provider_type, source_id, request_id,
                        google_device_id, display_name, settings_uri, media_sources_set,
                        poll_interval_seconds, created_at, updated_at, last_polled_at
                    ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        device.id,
                        device.provider_account_id,
                        device.provider_type,
                        device.source_id,
                        device.request_id,
                        device.google_device_id,
                        device.display_name,
                        device.settings_uri,
                        bool_to_int(device.media_sources_set),
                        device.poll_interval_seconds,
                        device.created_at,
                        device.updated_at,
                        device.last_polled_at,
                    ),
                )
            else:
                conn.execute(
                    """
                    update provider_devices
                    set provider_account_id = ?, request_id = ?, google_device_id = ?,
                        display_name = ?, settings_uri = ?, media_sources_set = ?,
                        poll_interval_seconds = ?, updated_at = ?, last_polled_at = ?
                    where provider_type = ? and source_id = ?
                    """,
                    (
                        device.provider_account_id,
                        device.request_id,
                        device.google_device_id,
                        device.display_name,
                        device.settings_uri,
                        bool_to_int(device.media_sources_set),
                        device.poll_interval_seconds,
                        device.updated_at,
                        device.last_polled_at,
                        _PROVIDER_TYPE,
                        device.source_id,
                    ),
                )
        return self.get_device(device.source_id) or device

    def replace_media_sources(
        self,
        *,
        source_id: str,
        provider_device_id: str,
        media_sources: list[tuple[str, str, str]],
        timestamp: str,
    ) -> list[GooglePhotosMediaSource]:
        existing_by_external: dict[str, GooglePhotosMediaSource] = {
            source.media_source_id: source
            for source in self.list_media_sources(source_id=source_id, include_disabled=True)
        }
        seen_external_ids = {item[0] for item in media_sources}
        with get_connection() as conn:
            if is_null_connection(conn):
                return []
            for external_id, display_name, kind in media_sources:
                existing = existing_by_external.get(external_id)
                if existing is None:
                    internal_id = f"google-media-source-{external_id}"
                    conn.execute(
                        """
                        insert into provider_media_sources (
                            id, provider_device_id, provider_type, source_id, media_source_id,
                            display_name, kind, enabled, asset_count, created_at, updated_at, last_seen_at
                        ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            internal_id,
                            provider_device_id,
                            _PROVIDER_TYPE,
                            source_id,
                            external_id,
                            display_name,
                            kind,
                            1,
                            0,
                            timestamp,
                            timestamp,
                            timestamp,
                        ),
                    )
                else:
                    conn.execute(
                        """
                        update provider_media_sources
                        set provider_device_id = ?, display_name = ?, kind = ?, enabled = 1,
                            updated_at = ?, last_seen_at = ?
                        where id = ?
                        """,
                        (provider_device_id, display_name, kind, timestamp, timestamp, existing.id),
                    )
            if seen_external_ids:
                placeholders = ", ".join("?" for _ in seen_external_ids)
                conn.execute(
                    f"""
                    update provider_media_sources
                    set enabled = 0, updated_at = ?
                    where provider_type = ? and source_id = ? and media_source_id not in ({placeholders})
                    """,
                    (timestamp, _PROVIDER_TYPE, source_id, *tuple(seen_external_ids)),
                )
            else:
                conn.execute(
                    """
                    update provider_media_sources
                    set enabled = 0, updated_at = ?
                    where provider_type = ? and source_id = ?
                    """,
                    (timestamp, _PROVIDER_TYPE, source_id),
                )
        self.update_media_source_asset_counts(source_id)
        return self.list_media_sources(source_id=source_id)

    def list_media_sources(self, *, source_id: str, include_disabled: bool = False) -> list[GooglePhotosMediaSource]:
        with get_connection() as conn:
            if is_null_connection(conn):
                return []
            query = "select * from provider_media_sources where provider_type = ? and source_id = ?"
            params: list[object] = [_PROVIDER_TYPE, source_id]
            if not include_disabled:
                query += " and enabled = 1"
            query += " order by lower(display_name) asc, media_source_id asc"
            cursor = conn.execute(query, tuple(params))
            return [self._media_source_from_row(row) for row in rows_to_dicts(cursor, cursor.fetchall())]

    def get_media_source(self, *, source_id: str, media_source_id: str) -> GooglePhotosMediaSource | None:
        with get_connection() as conn:
            if is_null_connection(conn):
                return None
            cursor = conn.execute(
                """
                select *
                from provider_media_sources
                where provider_type = ? and source_id = ? and media_source_id = ?
                limit 1
                """,
                (_PROVIDER_TYPE, source_id, media_source_id),
            )
            row = row_to_dict(cursor, cursor.fetchone())
            return None if row is None else self._media_source_from_row(row)

    def update_media_source_asset_counts(self, source_id: str) -> None:
        with get_connection() as conn:
            if is_null_connection(conn):
                return
            cursor = conn.execute(
                """
                select pms.id, count(pas.provider_asset_id) as asset_count
                from provider_media_sources pms
                left join provider_asset_sources pas on pas.provider_media_source_id = pms.id
                left join provider_assets pa on pa.id = pas.provider_asset_id and pa.is_active = 1
                where pms.provider_type = ? and pms.source_id = ?
                group by pms.id
                """,
                (_PROVIDER_TYPE, source_id),
            )
            for row in rows_to_dicts(cursor, cursor.fetchall()):
                conn.execute(
                    "update provider_media_sources set asset_count = ?, updated_at = ? where id = ?",
                    (int(row["asset_count"] or 0), utc_now(), str(row["id"])),
                )

    def get_running_or_queued_sync_run(self, source_id: str) -> GooglePhotosSyncRun | None:
        with get_connection() as conn:
            if is_null_connection(conn):
                return None
            cursor = conn.execute(
                """
                select * from provider_sync_runs
                where provider_type = ? and source_id = ? and status in ('queued', 'running')
                order by started_at asc, id asc
                limit 1
                """,
                (_PROVIDER_TYPE, source_id),
            )
            row = row_to_dict(cursor, cursor.fetchone())
            return None if row is None else self._sync_run_from_row(row)

    def get_oldest_queued_sync_run(self, source_id: str) -> GooglePhotosSyncRun | None:
        with get_connection() as conn:
            if is_null_connection(conn):
                return None
            cursor = conn.execute(
                """
                select * from provider_sync_runs
                where provider_type = ? and source_id = ? and status = 'queued'
                order by started_at asc, id asc
                limit 1
                """,
                (_PROVIDER_TYPE, source_id),
            )
            row = row_to_dict(cursor, cursor.fetchone())
            return None if row is None else self._sync_run_from_row(row)

    def create_sync_run(self, run: GooglePhotosSyncRun) -> GooglePhotosSyncRun:
        with get_connection() as conn:
            if is_null_connection(conn):
                return run
            conn.execute(
                """
                insert into provider_sync_runs (
                    id, provider_type, source_id, trigger, status, message, warning,
                    started_at, completed_at, discovered_count, imported_count,
                    updated_count, removed_count, skipped_count, error_count
                ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run.id,
                    run.provider_type,
                    run.source_id,
                    run.trigger,
                    run.status,
                    run.message,
                    run.warning,
                    run.started_at,
                    run.completed_at,
                    run.discovered_count,
                    run.imported_count,
                    run.updated_count,
                    run.removed_count,
                    run.skipped_count,
                    run.error_count,
                ),
            )
        return self.get_sync_run(run.id) or run

    def update_sync_run(self, run: GooglePhotosSyncRun) -> GooglePhotosSyncRun:
        with get_connection() as conn:
            if is_null_connection(conn):
                return run
            conn.execute(
                """
                update provider_sync_runs
                set trigger = ?, status = ?, message = ?, warning = ?, started_at = ?,
                    completed_at = ?, discovered_count = ?, imported_count = ?, updated_count = ?,
                    removed_count = ?, skipped_count = ?, error_count = ?
                where id = ?
                """,
                (
                    run.trigger,
                    run.status,
                    run.message,
                    run.warning,
                    run.started_at,
                    run.completed_at,
                    run.discovered_count,
                    run.imported_count,
                    run.updated_count,
                    run.removed_count,
                    run.skipped_count,
                    run.error_count,
                    run.id,
                ),
            )
        return self.get_sync_run(run.id) or run

    def get_sync_run(self, run_id: str) -> GooglePhotosSyncRun | None:
        with get_connection() as conn:
            if is_null_connection(conn):
                return None
            cursor = conn.execute("select * from provider_sync_runs where id = ?", (run_id,))
            row = row_to_dict(cursor, cursor.fetchone())
            return None if row is None else self._sync_run_from_row(row)

    def get_latest_sync_run(self, source_id: str) -> GooglePhotosSyncRun | None:
        with get_connection() as conn:
            if is_null_connection(conn):
                return None
            cursor = conn.execute(
                """
                select * from provider_sync_runs
                where provider_type = ? and source_id = ?
                order by started_at desc, id desc
                limit 1
                """,
                (_PROVIDER_TYPE, source_id),
            )
            row = row_to_dict(cursor, cursor.fetchone())
            return None if row is None else self._sync_run_from_row(row)

    def get_latest_successful_sync_run(self, source_id: str) -> GooglePhotosSyncRun | None:
        with get_connection() as conn:
            if is_null_connection(conn):
                return None
            placeholders = ", ".join("?" for _ in _SUCCESSFUL_SYNC_STATUSES)
            cursor = conn.execute(
                f"""
                select * from provider_sync_runs
                where provider_type = ? and source_id = ? and status in ({placeholders})
                order by completed_at desc, started_at desc, id desc
                limit 1
                """,
                (_PROVIDER_TYPE, source_id, *_SUCCESSFUL_SYNC_STATUSES),
            )
            row = row_to_dict(cursor, cursor.fetchone())
            return None if row is None else self._sync_run_from_row(row)

    def get_provider_asset(self, *, source_id: str, remote_media_id: str) -> GooglePhotosProviderAsset | None:
        with get_connection() as conn:
            if is_null_connection(conn):
                return None
            cursor = conn.execute(
                """
                select * from provider_assets
                where provider_type = ? and source_id = ? and remote_media_id = ?
                limit 1
                """,
                (_PROVIDER_TYPE, source_id, remote_media_id),
            )
            row = row_to_dict(cursor, cursor.fetchone())
        if row is None:
            return None
        asset = self._provider_asset_from_row(row)
        asset.media_source_ids = self.list_provider_asset_source_ids(asset.id)
        return asset

    def upsert_provider_asset(self, asset: GooglePhotosProviderAsset) -> GooglePhotosProviderAsset:
        with get_connection() as conn:
            if is_null_connection(conn):
                return asset
            existing = conn.execute(
                """
                select id from provider_assets
                where provider_type = ? and source_id = ? and remote_media_id = ?
                limit 1
                """,
                (_PROVIDER_TYPE, asset.source_id, asset.remote_media_id),
            ).fetchone()
            if existing is None:
                conn.execute(
                    """
                    insert into provider_assets (
                        id, provider_type, source_id, provider_account_id, remote_media_id,
                        mime_type, width, height, create_time, base_url, local_asset_id,
                        local_original_path, checksum_sha256, is_active, metadata_json,
                        first_synced_at, last_synced_at
                    ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        asset.id,
                        asset.provider_type,
                        asset.source_id,
                        asset.provider_account_id,
                        asset.remote_media_id,
                        asset.mime_type,
                        asset.width,
                        asset.height,
                        asset.create_time,
                        asset.base_url,
                        asset.local_asset_id,
                        asset.local_original_path,
                        asset.checksum_sha256,
                        bool_to_int(asset.is_active),
                        asset.metadata_json,
                        asset.first_synced_at,
                        asset.last_synced_at,
                    ),
                )
            else:
                conn.execute(
                    """
                    update provider_assets
                    set provider_account_id = ?, mime_type = ?, width = ?, height = ?,
                        create_time = ?, base_url = ?, local_asset_id = ?, local_original_path = ?,
                        checksum_sha256 = ?, is_active = ?, metadata_json = ?, last_synced_at = ?
                    where provider_type = ? and source_id = ? and remote_media_id = ?
                    """,
                    (
                        asset.provider_account_id,
                        asset.mime_type,
                        asset.width,
                        asset.height,
                        asset.create_time,
                        asset.base_url,
                        asset.local_asset_id,
                        asset.local_original_path,
                        asset.checksum_sha256,
                        bool_to_int(asset.is_active),
                        asset.metadata_json,
                        asset.last_synced_at,
                        _PROVIDER_TYPE,
                        asset.source_id,
                        asset.remote_media_id,
                    ),
                )
        refreshed = self.get_provider_asset(source_id=asset.source_id, remote_media_id=asset.remote_media_id)
        return refreshed or asset

    def list_provider_asset_source_ids(self, provider_asset_id: str) -> list[str]:
        with get_connection() as conn:
            if is_null_connection(conn):
                return []
            cursor = conn.execute(
                """
                select provider_media_source_id
                from provider_asset_sources
                where provider_asset_id = ?
                order by provider_media_source_id asc
                """,
                (provider_asset_id,),
            )
            return [str(row[0]) for row in cursor.fetchall()]

    def replace_provider_asset_source_links(
        self,
        *,
        provider_asset_id: str,
        provider_media_source_ids: Iterable[str],
        timestamp: str,
    ) -> None:
        desired = set(provider_media_source_ids)
        with get_connection() as conn:
            if is_null_connection(conn):
                return
            cursor = conn.execute(
                "select provider_media_source_id from provider_asset_sources where provider_asset_id = ?",
                (provider_asset_id,),
            )
            existing = {str(row[0]) for row in cursor.fetchall()}
            for media_source_id in desired - existing:
                conn.execute(
                    "insert into provider_asset_sources (provider_asset_id, provider_media_source_id, added_at) values (?, ?, ?)",
                    (provider_asset_id, media_source_id, timestamp),
                )
            for media_source_id in existing - desired:
                conn.execute(
                    "delete from provider_asset_sources where provider_asset_id = ? and provider_media_source_id = ?",
                    (provider_asset_id, media_source_id),
                )

    def mark_missing_provider_assets_inactive(self, *, source_id: str, seen_remote_ids: set[str], timestamp: str) -> list[str]:
        with get_connection() as conn:
            if is_null_connection(conn):
                return []
            cursor = conn.execute(
                "select id, remote_media_id, local_asset_id from provider_assets where provider_type = ? and source_id = ? and is_active = 1",
                (_PROVIDER_TYPE, source_id),
            )
            to_deactivate: list[tuple[str, str, str | None]] = []
            for row in cursor.fetchall():
                provider_asset_id, remote_media_id, local_asset_id = row
                if str(remote_media_id) not in seen_remote_ids:
                    to_deactivate.append((str(provider_asset_id), str(remote_media_id), None if local_asset_id is None else str(local_asset_id)))
            for provider_asset_id, _remote_media_id, _local_asset_id in to_deactivate:
                conn.execute(
                    "update provider_assets set is_active = 0, last_synced_at = ? where id = ?",
                    (timestamp, provider_asset_id),
                )
                conn.execute("delete from provider_asset_sources where provider_asset_id = ?", (provider_asset_id,))
            return [local_asset_id for _id, _remote_id, local_asset_id in to_deactivate if local_asset_id]

    def count_cached_assets(self, source_id: str) -> int:
        with get_connection() as conn:
            if is_null_connection(conn):
                return 0
            cursor = conn.execute(
                """
                select count(*)
                from provider_assets
                where provider_type = ? and source_id = ? and is_active = 1 and local_asset_id is not null
                """,
                (_PROVIDER_TYPE, source_id),
            )
            return int(cursor.fetchone()[0])

    def _auth_flow_from_row(self, row: dict[str, object]) -> GooglePhotosAuthFlow:
        return GooglePhotosAuthFlow(
            id=str(row["id"]),
            provider_type=str(row["provider_type"]),
            source_id=str(row["source_id"]),
            request_id=str(row["request_id"]),
            device_code=str(row["device_code"]),
            user_code=str(row["user_code"]),
            verification_uri=str(row["verification_uri"]),
            interval_seconds=int(row["interval_seconds"]),
            expires_at=str(row["expires_at"]),
            status=str(row["status"]),
            error_message=str(row["error_message"] or ""),
            device_display_name=str(row["device_display_name"]),
            created_at=str(row["created_at"]),
            updated_at=str(row["updated_at"]),
            completed_at=None if row["completed_at"] is None else str(row["completed_at"]),
        )

    def _account_from_row(self, row: dict[str, object]) -> GooglePhotosAccount:
        return GooglePhotosAccount(
            id=str(row["id"]),
            provider_type=str(row["provider_type"]),
            source_id=str(row["source_id"]),
            connection_state=str(row["connection_state"]),
            account_subject=None if row["account_subject"] is None else str(row["account_subject"]),
            account_email=None if row["account_email"] is None else str(row["account_email"]),
            account_display_name=None if row["account_display_name"] is None else str(row["account_display_name"]),
            account_picture_url=None if row["account_picture_url"] is None else str(row["account_picture_url"]),
            access_token=None if row["access_token"] is None else str(row["access_token"]),
            refresh_token=None if row["refresh_token"] is None else str(row["refresh_token"]),
            scope=str(row["scope"] or ""),
            access_token_expires_at=None
            if row["access_token_expires_at"] is None
            else str(row["access_token_expires_at"]),
            connected_at=None if row["connected_at"] is None else str(row["connected_at"]),
            disconnected_at=None if row["disconnected_at"] is None else str(row["disconnected_at"]),
            last_error=str(row["last_error"] or ""),
            created_at=str(row["created_at"]),
            updated_at=str(row["updated_at"]),
        )

    def _device_from_row(self, row: dict[str, object]) -> GooglePhotosDevice:
        return GooglePhotosDevice(
            id=str(row["id"]),
            provider_account_id=str(row["provider_account_id"]),
            provider_type=str(row["provider_type"]),
            source_id=str(row["source_id"]),
            request_id=str(row["request_id"]),
            google_device_id=None if row["google_device_id"] is None else str(row["google_device_id"]),
            display_name=str(row["display_name"]),
            settings_uri=None if row["settings_uri"] is None else str(row["settings_uri"]),
            media_sources_set=int_to_bool(row["media_sources_set"]),
            poll_interval_seconds=int(row["poll_interval_seconds"] or 60),
            created_at=str(row["created_at"]),
            updated_at=str(row["updated_at"]),
            last_polled_at=None if row["last_polled_at"] is None else str(row["last_polled_at"]),
        )

    def _media_source_from_row(self, row: dict[str, object]) -> GooglePhotosMediaSource:
        return GooglePhotosMediaSource(
            id=str(row["id"]),
            provider_device_id=str(row["provider_device_id"]),
            provider_type=str(row["provider_type"]),
            source_id=str(row["source_id"]),
            media_source_id=str(row["media_source_id"]),
            display_name=str(row["display_name"]),
            kind=str(row["kind"] or "ambient_media_source"),
            enabled=int_to_bool(row["enabled"]),
            asset_count=int(row["asset_count"] or 0),
            created_at=str(row["created_at"]),
            updated_at=str(row["updated_at"]),
            last_seen_at=str(row["last_seen_at"]),
        )

    def _sync_run_from_row(self, row: dict[str, object]) -> GooglePhotosSyncRun:
        return GooglePhotosSyncRun(
            id=str(row["id"]),
            provider_type=str(row["provider_type"]),
            source_id=str(row["source_id"]),
            trigger=str(row["trigger"]),
            status=str(row["status"]),
            message=str(row["message"] or ""),
            warning=str(row["warning"] or ""),
            started_at=str(row["started_at"]),
            completed_at=None if row["completed_at"] is None else str(row["completed_at"]),
            discovered_count=int(row["discovered_count"] or 0),
            imported_count=int(row["imported_count"] or 0),
            updated_count=int(row["updated_count"] or 0),
            removed_count=int(row["removed_count"] or 0),
            skipped_count=int(row["skipped_count"] or 0),
            error_count=int(row["error_count"] or 0),
        )

    def _provider_asset_from_row(self, row: dict[str, object]) -> GooglePhotosProviderAsset:
        return GooglePhotosProviderAsset(
            id=str(row["id"]),
            provider_type=str(row["provider_type"]),
            source_id=str(row["source_id"]),
            provider_account_id=None if row["provider_account_id"] is None else str(row["provider_account_id"]),
            remote_media_id=str(row["remote_media_id"]),
            mime_type=str(row["mime_type"]),
            width=int(row["width"] or 0),
            height=int(row["height"] or 0),
            create_time=None if row["create_time"] is None else str(row["create_time"]),
            base_url=str(row["base_url"]),
            local_asset_id=None if row["local_asset_id"] is None else str(row["local_asset_id"]),
            local_original_path=None if row["local_original_path"] is None else str(row["local_original_path"]),
            checksum_sha256=None if row["checksum_sha256"] is None else str(row["checksum_sha256"]),
            is_active=int_to_bool(row["is_active"]),
            metadata_json=str(row["metadata_json"] or "{}"),
            first_synced_at=str(row["first_synced_at"]),
            last_synced_at=str(row["last_synced_at"]),
            media_source_ids=[],
        )

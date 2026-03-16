from __future__ import annotations

from uuid import uuid4

from app.db.connection import get_connection, is_null_connection
from app.providers.google_photos.metadata import PROVIDER_NAME
from app.providers.google_photos.models import (
    GooglePhotosAccount,
    GooglePhotosAuthFlow,
    GooglePhotosMediaSource,
    GooglePhotosProviderAsset,
    GooglePhotosSyncRun,
)
from app.repositories.base import bool_to_int, int_to_bool, json_dumps, json_loads, row_to_dict, rows_to_dicts, utc_now


class GooglePhotosRepository:
    def get_account(self) -> GooglePhotosAccount | None:
        with get_connection() as conn:
            if is_null_connection(conn):
                return None
            cursor = conn.execute("select * from provider_accounts where provider_name = ?", (PROVIDER_NAME,))
            row = row_to_dict(cursor, cursor.fetchone())
        return None if row is None else self._account_from_row(row)

    def upsert_account(self, account: GooglePhotosAccount) -> GooglePhotosAccount:
        with get_connection() as conn:
            if is_null_connection(conn):
                return account
            existing = conn.execute("select id from provider_accounts where provider_name = ?", (PROVIDER_NAME,)).fetchone()
            values = (
                account.id,
                account.provider_name,
                account.connection_state,
                account.account_subject,
                account.account_email,
                account.account_display_name,
                account.account_picture_url,
                account.access_token,
                account.refresh_token,
                account.scope,
                account.access_token_expires_at,
                account.request_id,
                account.device_id,
                account.device_display_name,
                account.settings_uri,
                bool_to_int(account.media_sources_set),
                account.device_poll_interval_seconds,
                account.device_created_at,
                account.last_device_poll_at,
                account.connected_at,
                account.disconnected_at,
                account.last_sync_requested_at,
                account.last_completed_sync_at,
                account.current_error,
                account.created_at,
                account.updated_at,
            )
            if existing is None:
                conn.execute(
                    """
                    insert into provider_accounts (
                        id, provider_name, connection_state, account_subject, account_email, account_display_name,
                        account_picture_url, access_token, refresh_token, scope, access_token_expires_at,
                        request_id, device_id, device_display_name, settings_uri, media_sources_set,
                        device_poll_interval_seconds, device_created_at, last_device_poll_at, connected_at,
                        disconnected_at, last_sync_requested_at, last_completed_sync_at, current_error,
                        created_at, updated_at
                    ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    values,
                )
            else:
                conn.execute(
                    """
                    update provider_accounts
                    set id = ?, connection_state = ?, account_subject = ?, account_email = ?, account_display_name = ?,
                        account_picture_url = ?, access_token = ?, refresh_token = ?, scope = ?, access_token_expires_at = ?,
                        request_id = ?, device_id = ?, device_display_name = ?, settings_uri = ?, media_sources_set = ?,
                        device_poll_interval_seconds = ?, device_created_at = ?, last_device_poll_at = ?, connected_at = ?,
                        disconnected_at = ?, last_sync_requested_at = ?, last_completed_sync_at = ?, current_error = ?,
                        created_at = ?, updated_at = ?
                    where provider_name = ?
                    """,
                    (
                        account.id,
                        account.connection_state,
                        account.account_subject,
                        account.account_email,
                        account.account_display_name,
                        account.account_picture_url,
                        account.access_token,
                        account.refresh_token,
                        account.scope,
                        account.access_token_expires_at,
                        account.request_id,
                        account.device_id,
                        account.device_display_name,
                        account.settings_uri,
                        bool_to_int(account.media_sources_set),
                        account.device_poll_interval_seconds,
                        account.device_created_at,
                        account.last_device_poll_at,
                        account.connected_at,
                        account.disconnected_at,
                        account.last_sync_requested_at,
                        account.last_completed_sync_at,
                        account.current_error,
                        account.created_at,
                        account.updated_at,
                        PROVIDER_NAME,
                    ),
                )
        return self.get_account() or account

    def create_default_account(self) -> GooglePhotosAccount:
        now = utc_now()
        return GooglePhotosAccount(
            id=f"provider-account-{uuid4().hex[:12]}",
            provider_name=PROVIDER_NAME,
            connection_state="disconnected",
            account_subject=None,
            account_email=None,
            account_display_name=None,
            account_picture_url=None,
            access_token=None,
            refresh_token=None,
            scope="",
            access_token_expires_at=None,
            request_id=None,
            device_id=None,
            device_display_name=None,
            settings_uri=None,
            media_sources_set=False,
            device_poll_interval_seconds=30,
            device_created_at=None,
            last_device_poll_at=None,
            connected_at=None,
            disconnected_at=None,
            last_sync_requested_at=None,
            last_completed_sync_at=None,
            current_error="",
            created_at=now,
            updated_at=now,
        )

    def get_latest_auth_flow(self, *, include_completed: bool = True) -> GooglePhotosAuthFlow | None:
        query = "select * from provider_auth_flows where provider_name = ?"
        params: tuple[object, ...] = (PROVIDER_NAME,)
        if not include_completed:
            query += " and status in ('pending', 'polling')"
        query += " order by created_at desc, id desc limit 1"
        with get_connection() as conn:
            if is_null_connection(conn):
                return None
            cursor = conn.execute(query, params)
            row = row_to_dict(cursor, cursor.fetchone())
        return None if row is None else self._auth_flow_from_row(row)

    def cancel_active_auth_flows(self) -> None:
        now = utc_now()
        with get_connection() as conn:
            if is_null_connection(conn):
                return
            conn.execute(
                """
                update provider_auth_flows
                set status = 'cancelled', updated_at = ?, completed_at = ?
                where provider_name = ? and status in ('pending', 'polling')
                """,
                (now, now, PROVIDER_NAME),
            )

    def create_auth_flow(self, flow: GooglePhotosAuthFlow) -> GooglePhotosAuthFlow:
        with get_connection() as conn:
            if is_null_connection(conn):
                return flow
            conn.execute(
                """
                insert into provider_auth_flows (
                    id, provider_name, status, request_id, device_display_name, device_code, user_code,
                    verification_uri, verification_uri_complete, interval_seconds, expires_at, last_polled_at,
                    next_poll_at, error_message, created_at, updated_at, completed_at
                ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    flow.id,
                    flow.provider_name,
                    flow.status,
                    flow.request_id,
                    flow.device_display_name,
                    flow.device_code,
                    flow.user_code,
                    flow.verification_uri,
                    flow.verification_uri_complete,
                    flow.interval_seconds,
                    flow.expires_at,
                    flow.last_polled_at,
                    flow.next_poll_at,
                    flow.error_message,
                    flow.created_at,
                    flow.updated_at,
                    flow.completed_at,
                ),
            )
        return self.get_latest_auth_flow() or flow

    def update_auth_flow(self, flow: GooglePhotosAuthFlow) -> GooglePhotosAuthFlow:
        with get_connection() as conn:
            if is_null_connection(conn):
                return flow
            conn.execute(
                """
                update provider_auth_flows
                set status = ?, request_id = ?, device_display_name = ?, device_code = ?, user_code = ?,
                    verification_uri = ?, verification_uri_complete = ?, interval_seconds = ?, expires_at = ?,
                    last_polled_at = ?, next_poll_at = ?, error_message = ?, created_at = ?, updated_at = ?, completed_at = ?
                where id = ?
                """,
                (
                    flow.status,
                    flow.request_id,
                    flow.device_display_name,
                    flow.device_code,
                    flow.user_code,
                    flow.verification_uri,
                    flow.verification_uri_complete,
                    flow.interval_seconds,
                    flow.expires_at,
                    flow.last_polled_at,
                    flow.next_poll_at,
                    flow.error_message,
                    flow.created_at,
                    flow.updated_at,
                    flow.completed_at,
                    flow.id,
                ),
            )
        return self.get_latest_auth_flow() or flow

    def replace_media_sources(self, media_sources: list[GooglePhotosMediaSource]) -> None:
        with get_connection() as conn:
            if is_null_connection(conn):
                return
            conn.execute("delete from provider_media_sources where provider_name = ?", (PROVIDER_NAME,))
            for media_source in media_sources:
                conn.execute(
                    """
                    insert into provider_media_sources (
                        id, provider_name, media_source_id, display_name, is_selected, last_seen_at, created_at, updated_at
                    ) values (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        media_source.id,
                        media_source.provider_name,
                        media_source.media_source_id,
                        media_source.display_name,
                        bool_to_int(media_source.is_selected),
                        media_source.last_seen_at,
                        media_source.created_at,
                        media_source.updated_at,
                    ),
                )

    def list_media_sources(self) -> list[GooglePhotosMediaSource]:
        with get_connection() as conn:
            if is_null_connection(conn):
                return []
            cursor = conn.execute(
                "select * from provider_media_sources where provider_name = ? order by lower(display_name) asc, media_source_id asc",
                (PROVIDER_NAME,),
            )
            rows = rows_to_dicts(cursor, cursor.fetchall())
        return [self._media_source_from_row(row) for row in rows]

    def create_sync_run(self, sync_run: GooglePhotosSyncRun) -> GooglePhotosSyncRun:
        with get_connection() as conn:
            if is_null_connection(conn):
                return sync_run
            conn.execute(
                """
                insert into provider_sync_runs (
                    id, provider_name, trigger, status, message, error_message, warning_messages_json,
                    discovered_count, imported_count, duplicate_count, skipped_count, error_count,
                    started_at, completed_at
                ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    sync_run.id,
                    sync_run.provider_name,
                    sync_run.trigger,
                    sync_run.status,
                    sync_run.message,
                    sync_run.error_message,
                    json_dumps(sync_run.warning_messages),
                    sync_run.discovered_count,
                    sync_run.imported_count,
                    sync_run.duplicate_count,
                    sync_run.skipped_count,
                    sync_run.error_count,
                    sync_run.started_at,
                    sync_run.completed_at,
                ),
            )
        return self.get_sync_run(sync_run.id) or sync_run

    def update_sync_run(self, sync_run: GooglePhotosSyncRun) -> GooglePhotosSyncRun:
        with get_connection() as conn:
            if is_null_connection(conn):
                return sync_run
            conn.execute(
                """
                update provider_sync_runs
                set trigger = ?, status = ?, message = ?, error_message = ?, warning_messages_json = ?,
                    discovered_count = ?, imported_count = ?, duplicate_count = ?, skipped_count = ?, error_count = ?,
                    started_at = ?, completed_at = ?
                where id = ?
                """,
                (
                    sync_run.trigger,
                    sync_run.status,
                    sync_run.message,
                    sync_run.error_message,
                    json_dumps(sync_run.warning_messages),
                    sync_run.discovered_count,
                    sync_run.imported_count,
                    sync_run.duplicate_count,
                    sync_run.skipped_count,
                    sync_run.error_count,
                    sync_run.started_at,
                    sync_run.completed_at,
                    sync_run.id,
                ),
            )
        return self.get_sync_run(sync_run.id) or sync_run

    def get_sync_run(self, sync_run_id: str) -> GooglePhotosSyncRun | None:
        with get_connection() as conn:
            if is_null_connection(conn):
                return None
            cursor = conn.execute("select * from provider_sync_runs where id = ?", (sync_run_id,))
            row = row_to_dict(cursor, cursor.fetchone())
        return None if row is None else self._sync_run_from_row(row)

    def get_latest_sync_run(self) -> GooglePhotosSyncRun | None:
        with get_connection() as conn:
            if is_null_connection(conn):
                return None
            cursor = conn.execute(
                "select * from provider_sync_runs where provider_name = ? order by started_at desc, id desc limit 1",
                (PROVIDER_NAME,),
            )
            row = row_to_dict(cursor, cursor.fetchone())
        return None if row is None else self._sync_run_from_row(row)

    def get_provider_asset(self, remote_media_id: str) -> GooglePhotosProviderAsset | None:
        with get_connection() as conn:
            if is_null_connection(conn):
                return None
            cursor = conn.execute(
                "select * from provider_assets where provider_name = ? and remote_media_id = ?",
                (PROVIDER_NAME, remote_media_id),
            )
            row = row_to_dict(cursor, cursor.fetchone())
        if row is None:
            return None
        return self._attach_asset_media_sources(self._provider_asset_from_row(row))

    def upsert_provider_asset(self, provider_asset: GooglePhotosProviderAsset) -> GooglePhotosProviderAsset:
        with get_connection() as conn:
            if is_null_connection(conn):
                return provider_asset
            existing = conn.execute(
                "select id from provider_assets where provider_name = ? and remote_media_id = ?",
                (PROVIDER_NAME, provider_asset.remote_media_id),
            ).fetchone()
            values = (
                provider_asset.id,
                provider_asset.provider_name,
                provider_asset.remote_media_id,
                provider_asset.local_asset_id,
                provider_asset.mime_type,
                provider_asset.width,
                provider_asset.height,
                provider_asset.create_time,
                provider_asset.imported_from_path,
                provider_asset.remote_base_url,
                provider_asset.cached_original_path,
                provider_asset.checksum_sha256,
                provider_asset.metadata_json,
                provider_asset.first_synced_at,
                provider_asset.last_synced_at,
                provider_asset.last_seen_at,
                bool_to_int(provider_asset.is_active),
            )
            if existing is None:
                conn.execute(
                    """
                    insert into provider_assets (
                        id, provider_name, remote_media_id, local_asset_id, mime_type, width, height, create_time,
                        imported_from_path, remote_base_url, cached_original_path, checksum_sha256, metadata_json,
                        first_synced_at, last_synced_at, last_seen_at, is_active
                    ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    values,
                )
            else:
                conn.execute(
                    """
                    update provider_assets
                    set id = ?, local_asset_id = ?, mime_type = ?, width = ?, height = ?, create_time = ?,
                        imported_from_path = ?, remote_base_url = ?, cached_original_path = ?, checksum_sha256 = ?,
                        metadata_json = ?, first_synced_at = ?, last_synced_at = ?, last_seen_at = ?, is_active = ?
                    where provider_name = ? and remote_media_id = ?
                    """,
                    (
                        provider_asset.id,
                        provider_asset.local_asset_id,
                        provider_asset.mime_type,
                        provider_asset.width,
                        provider_asset.height,
                        provider_asset.create_time,
                        provider_asset.imported_from_path,
                        provider_asset.remote_base_url,
                        provider_asset.cached_original_path,
                        provider_asset.checksum_sha256,
                        provider_asset.metadata_json,
                        provider_asset.first_synced_at,
                        provider_asset.last_synced_at,
                        provider_asset.last_seen_at,
                        bool_to_int(provider_asset.is_active),
                        PROVIDER_NAME,
                        provider_asset.remote_media_id,
                    ),
                )
            conn.execute("delete from provider_asset_media_sources where provider_asset_id = ?", (provider_asset.id,))
            for media_source_id in provider_asset.media_source_ids:
                conn.execute(
                    "insert into provider_asset_media_sources (provider_asset_id, media_source_id, added_at) values (?, ?, ?)",
                    (provider_asset.id, media_source_id, provider_asset.last_seen_at),
                )
        return self.get_provider_asset(provider_asset.remote_media_id) or provider_asset

    def count_provider_assets(self) -> int:
        with get_connection() as conn:
            if is_null_connection(conn):
                return 0
            cursor = conn.execute(
                "select count(*) from provider_assets where provider_name = ? and is_active = 1",
                (PROVIDER_NAME,),
            )
            return int(cursor.fetchone()[0])

    def _attach_asset_media_sources(self, provider_asset: GooglePhotosProviderAsset) -> GooglePhotosProviderAsset:
        with get_connection() as conn:
            if is_null_connection(conn):
                return provider_asset
            cursor = conn.execute(
                "select media_source_id from provider_asset_media_sources where provider_asset_id = ? order by media_source_id asc",
                (provider_asset.id,),
            )
            provider_asset.media_source_ids = [str(row[0]) for row in cursor.fetchall()]
        return provider_asset

    @staticmethod
    def _account_from_row(row: dict[str, object]) -> GooglePhotosAccount:
        return GooglePhotosAccount(
            id=str(row["id"]),
            provider_name=str(row["provider_name"]),
            connection_state=str(row["connection_state"]),
            account_subject=None if row["account_subject"] is None else str(row["account_subject"]),
            account_email=None if row["account_email"] is None else str(row["account_email"]),
            account_display_name=None if row["account_display_name"] is None else str(row["account_display_name"]),
            account_picture_url=None if row["account_picture_url"] is None else str(row["account_picture_url"]),
            access_token=None if row["access_token"] is None else str(row["access_token"]),
            refresh_token=None if row["refresh_token"] is None else str(row["refresh_token"]),
            scope=str(row["scope"] or ""),
            access_token_expires_at=None if row["access_token_expires_at"] is None else str(row["access_token_expires_at"]),
            request_id=None if row["request_id"] is None else str(row["request_id"]),
            device_id=None if row["device_id"] is None else str(row["device_id"]),
            device_display_name=None if row["device_display_name"] is None else str(row["device_display_name"]),
            settings_uri=None if row["settings_uri"] is None else str(row["settings_uri"]),
            media_sources_set=int_to_bool(row["media_sources_set"]),
            device_poll_interval_seconds=int(row["device_poll_interval_seconds"] or 30),
            device_created_at=None if row["device_created_at"] is None else str(row["device_created_at"]),
            last_device_poll_at=None if row["last_device_poll_at"] is None else str(row["last_device_poll_at"]),
            connected_at=None if row["connected_at"] is None else str(row["connected_at"]),
            disconnected_at=None if row["disconnected_at"] is None else str(row["disconnected_at"]),
            last_sync_requested_at=None if row["last_sync_requested_at"] is None else str(row["last_sync_requested_at"]),
            last_completed_sync_at=None if row["last_completed_sync_at"] is None else str(row["last_completed_sync_at"]),
            current_error=str(row["current_error"] or ""),
            created_at=str(row["created_at"]),
            updated_at=str(row["updated_at"]),
        )

    @staticmethod
    def _auth_flow_from_row(row: dict[str, object]) -> GooglePhotosAuthFlow:
        return GooglePhotosAuthFlow(
            id=str(row["id"]),
            provider_name=str(row["provider_name"]),
            status=str(row["status"]),
            request_id=str(row["request_id"]),
            device_display_name=str(row["device_display_name"]),
            device_code=str(row["device_code"]),
            user_code=str(row["user_code"]),
            verification_uri=str(row["verification_uri"]),
            verification_uri_complete=None if row["verification_uri_complete"] is None else str(row["verification_uri_complete"]),
            interval_seconds=int(row["interval_seconds"]),
            expires_at=str(row["expires_at"]),
            error_message=str(row["error_message"] or ""),
            created_at=str(row["created_at"]),
            updated_at=str(row["updated_at"]),
            last_polled_at=None if row["last_polled_at"] is None else str(row["last_polled_at"]),
            next_poll_at=None if row["next_poll_at"] is None else str(row["next_poll_at"]),
            completed_at=None if row["completed_at"] is None else str(row["completed_at"]),
        )

    @staticmethod
    def _media_source_from_row(row: dict[str, object]) -> GooglePhotosMediaSource:
        return GooglePhotosMediaSource(
            id=str(row["id"]),
            provider_name=str(row["provider_name"]),
            media_source_id=str(row["media_source_id"]),
            display_name=str(row["display_name"]),
            is_selected=int_to_bool(row["is_selected"]),
            last_seen_at=str(row["last_seen_at"]),
            created_at=str(row["created_at"]),
            updated_at=str(row["updated_at"]),
        )

    @staticmethod
    def _sync_run_from_row(row: dict[str, object]) -> GooglePhotosSyncRun:
        return GooglePhotosSyncRun(
            id=str(row["id"]),
            provider_name=str(row["provider_name"]),
            trigger=str(row["trigger"]),
            status=str(row["status"]),
            message=str(row["message"] or ""),
            error_message=str(row["error_message"] or ""),
            warning_messages=json_loads(str(row["warning_messages_json"]), []),
            discovered_count=int(row["discovered_count"]),
            imported_count=int(row["imported_count"]),
            duplicate_count=int(row["duplicate_count"]),
            skipped_count=int(row["skipped_count"]),
            error_count=int(row["error_count"]),
            started_at=str(row["started_at"]),
            completed_at=None if row["completed_at"] is None else str(row["completed_at"]),
        )

    @staticmethod
    def _provider_asset_from_row(row: dict[str, object]) -> GooglePhotosProviderAsset:
        return GooglePhotosProviderAsset(
            id=str(row["id"]),
            provider_name=str(row["provider_name"]),
            remote_media_id=str(row["remote_media_id"]),
            local_asset_id=None if row["local_asset_id"] is None else str(row["local_asset_id"]),
            mime_type=str(row["mime_type"]),
            width=int(row["width"] or 0),
            height=int(row["height"] or 0),
            create_time=None if row["create_time"] is None else str(row["create_time"]),
            imported_from_path=str(row["imported_from_path"]),
            remote_base_url=str(row["remote_base_url"] or ""),
            cached_original_path=None if row["cached_original_path"] is None else str(row["cached_original_path"]),
            checksum_sha256=None if row["checksum_sha256"] is None else str(row["checksum_sha256"]),
            metadata_json=str(row["metadata_json"] or "{}"),
            first_synced_at=str(row["first_synced_at"]),
            last_synced_at=str(row["last_synced_at"]),
            last_seen_at=str(row["last_seen_at"]),
            is_active=int_to_bool(row["is_active"]),
        )

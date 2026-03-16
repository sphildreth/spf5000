from __future__ import annotations

import mimetypes
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from app.core.config import settings
from app.db.bootstrap import GOOGLE_PHOTOS_COLLECTION_ID, GOOGLE_PHOTOS_SOURCE_ID
from app.providers.google_photos.client import GooglePhotosClient
from app.providers.google_photos.errors import (
    GooglePhotosAuthorizationDenied,
    GooglePhotosAuthorizationExpired,
    GooglePhotosAuthorizationPending,
    GooglePhotosConfigurationError,
    GooglePhotosError,
    GooglePhotosSlowDown,
)
from app.providers.google_photos.metadata import HIGHLIGHTS_MEDIA_SOURCE_ID, PROVIDER_NAME
from app.providers.google_photos.models import (
    GooglePhotosAccount,
    GooglePhotosAuthFlow,
    GooglePhotosMediaSource,
    GooglePhotosProviderAsset,
    GooglePhotosRemoteMediaItem,
    GooglePhotosSyncRun,
)
from app.providers.google_photos.oauth import parse_duration_seconds, utc_plus_seconds
from app.providers.google_photos.sync import GooglePhotosSyncStats
from app.repositories.base import json_dumps, utc_now
from app.repositories.google_photos_repository import GooglePhotosRepository
from app.repositories.source_repository import SourceRepository
from app.services.asset_ingest_service import AssetIngestService


class GooglePhotosService:
    client_factory = GooglePhotosClient

    def __init__(
        self,
        repo: GooglePhotosRepository | None = None,
        asset_ingestion: AssetIngestService | None = None,
        source_repo: SourceRepository | None = None,
    ) -> None:
        self.repo = repo or GooglePhotosRepository()
        self.asset_ingestion = asset_ingestion or AssetIngestService()
        self.source_repo = source_repo or SourceRepository()

    def get_status(self) -> dict[str, object]:
        account = self._get_or_create_account()
        auth_flow = self.repo.get_latest_auth_flow(include_completed=False)
        media_sources = self.repo.list_media_sources()
        latest_sync_run = self.repo.get_latest_sync_run()
        cached_asset_count = self.repo.count_provider_assets()
        connection_state = account.connection_state
        current_error = account.current_error or None
        warnings: list[str] = []

        if auth_flow is not None:
            connection_state = "awaiting_authorization"
            warnings.append("Finish the Google device-code approval flow to link this frame.")
        if not settings.google_photos_configured:
            warnings.append("Google Photos OAuth client ID and secret are not configured.")
        if account.device_id and not account.media_sources_set:
            warnings.append("Use the Google Photos settings URI to select media sources before syncing.")
        if any(source.media_source_id == HIGHLIGHTS_MEDIA_SOURCE_ID for source in media_sources):
            warnings.append("Google Photos 'Highlights' is selected, but it cannot be enumerated per-source; sync skips it.")
        if cached_asset_count > 0 and connection_state != "connected":
            warnings.append("Cached Google Photos assets remain on disk for offline playback.")
        if latest_sync_run is not None:
            warnings.extend(message for message in latest_sync_run.warning_messages if message not in warnings)
        if auth_flow is not None and auth_flow.error_message and auth_flow.error_message not in warnings:
            warnings.append(auth_flow.error_message)
        if current_error and current_error not in warnings:
            warnings.append(current_error)

        linked_account = None
        if account.account_subject or account.account_email or account.account_display_name:
            linked_account = {
                "subject": account.account_subject,
                "email": account.account_email,
                "display_name": account.account_display_name,
                "picture_url": account.account_picture_url,
                "connected_at": account.connected_at,
            }

        device = None
        if account.request_id or account.device_id or account.device_display_name or account.settings_uri:
            device = {
                "request_id": account.request_id,
                "device_id": account.device_id,
                "display_name": account.device_display_name,
                "settings_uri": account.settings_uri,
                "media_sources_set": account.media_sources_set,
                "poll_interval_seconds": account.device_poll_interval_seconds,
                "device_created_at": account.device_created_at,
                "last_polled_at": account.last_device_poll_at,
            }

        return {
            "provider": PROVIDER_NAME,
            "provider_display_name": settings.google_photos_provider_display_name,
            "available": settings.google_photos_enabled,
            "configured": settings.google_photos_configured,
            "sync_cadence_seconds": settings.google_photos_sync_cadence_seconds,
            "connection_state": connection_state,
            "auth_flow": None if auth_flow is None else auth_flow,
            "linked_account": linked_account,
            "device": device,
            "selected_media_sources": media_sources,
            "latest_sync_run": latest_sync_run,
            "cached_asset_count": cached_asset_count,
            "current_error": current_error,
            "warnings": warnings,
        }

    def start_connect(self, *, device_display_name: str | None = None) -> dict[str, object]:
        self._ensure_configured()
        self.repo.cancel_active_auth_flows()
        now = utc_now()
        request_id = str(uuid4())
        display_name = device_display_name or settings.google_photos_provider_display_name
        client = self.client_factory()
        payload = client.start_device_flow(request_id=request_id, display_name=display_name)
        flow = GooglePhotosAuthFlow(
            id=f"provider-auth-{uuid4().hex[:12]}",
            provider_name=PROVIDER_NAME,
            status="pending",
            request_id=request_id,
            device_display_name=display_name,
            device_code=str(payload["device_code"]),
            user_code=str(payload["user_code"]),
            verification_uri=str(payload["verification_uri"]),
            verification_uri_complete=None if payload.get("verification_uri_complete") is None else str(payload["verification_uri_complete"]),
            interval_seconds=int(payload["interval_seconds"]),
            expires_at=str(payload["expires_at"]),
            error_message="",
            created_at=now,
            updated_at=now,
            next_poll_at=utc_plus_seconds(int(payload["interval_seconds"])),
        )
        self.repo.create_auth_flow(flow)

        account = self._get_or_create_account()
        account.connection_state = "awaiting_authorization"
        account.request_id = request_id
        account.device_display_name = display_name
        account.current_error = ""
        account.updated_at = now
        self.repo.upsert_account(account)
        return self.get_status()

    def poll_connect(self, *, flow_id: str | None = None) -> dict[str, object]:
        del flow_id
        auth_flow = self.repo.get_latest_auth_flow(include_completed=False)
        if auth_flow is None:
            account = self._get_or_create_account()
            if account.connection_state == "connected" and account.device_id:
                self._refresh_device_state(account, force=False)
            return self.get_status()

        now = utc_now()
        if auth_flow.next_poll_at and self._utc_now() < self._parse_timestamp(auth_flow.next_poll_at):
            return self.get_status()

        client = self.client_factory()
        try:
            token_payload = client.poll_device_flow(device_code=auth_flow.device_code)
        except GooglePhotosAuthorizationPending:
            auth_flow.status = "polling"
            auth_flow.error_message = ""
            auth_flow.last_polled_at = now
            auth_flow.next_poll_at = utc_plus_seconds(auth_flow.interval_seconds)
            auth_flow.updated_at = now
            self.repo.update_auth_flow(auth_flow)
            return self.get_status()
        except GooglePhotosSlowDown as exc:
            auth_flow.status = "polling"
            auth_flow.interval_seconds = max(auth_flow.interval_seconds + 5, exc.interval_seconds)
            auth_flow.last_polled_at = now
            auth_flow.next_poll_at = utc_plus_seconds(auth_flow.interval_seconds)
            auth_flow.updated_at = now
            auth_flow.error_message = str(exc)
            self.repo.update_auth_flow(auth_flow)
            return self.get_status()
        except (GooglePhotosAuthorizationDenied, GooglePhotosAuthorizationExpired) as exc:
            auth_flow.status = "failed"
            auth_flow.error_message = str(exc)
            auth_flow.last_polled_at = now
            auth_flow.updated_at = now
            auth_flow.completed_at = now
            self.repo.update_auth_flow(auth_flow)
            account = self._get_or_create_account()
            account.connection_state = "error"
            account.current_error = str(exc)
            account.updated_at = now
            self.repo.upsert_account(account)
            return self.get_status()

        account = self._get_or_create_account()
        account.access_token = str(token_payload.get("access_token") or "")
        account.refresh_token = str(token_payload.get("refresh_token") or account.refresh_token or "")
        account.scope = str(token_payload.get("scope") or account.scope or client.scope)
        expires_in = int(token_payload.get("expires_in", 3600) or 3600)
        account.access_token_expires_at = (self._utc_now() + timedelta(seconds=expires_in)).isoformat()
        userinfo = client.get_userinfo(account.access_token)
        account.account_subject = self._optional_str(userinfo.get("sub"))
        account.account_email = self._optional_str(userinfo.get("email"))
        account.account_display_name = self._optional_str(userinfo.get("name"))
        account.account_picture_url = self._optional_str(userinfo.get("picture"))
        device_payload = client.create_device(
            access_token=account.access_token,
            request_id=auth_flow.request_id,
            display_name=auth_flow.device_display_name,
        )
        self._apply_device_payload(account, device_payload, poll_at=now)
        account.connection_state = "connected"
        account.connected_at = account.connected_at or now
        account.disconnected_at = None
        account.current_error = ""
        account.updated_at = now
        self.repo.upsert_account(account)

        auth_flow.status = "completed"
        auth_flow.last_polled_at = now
        auth_flow.next_poll_at = None
        auth_flow.updated_at = now
        auth_flow.completed_at = now
        auth_flow.error_message = ""
        self.repo.update_auth_flow(auth_flow)
        return self.get_status()

    def disconnect(self) -> dict[str, object]:
        account = self._get_or_create_account()
        client = self.client_factory()
        if account.access_token:
            try:
                account = self._ensure_access_token(account)
                client.delete_device(access_token=account.access_token or "", device_id=account.device_id, request_id=account.request_id)
            except GooglePhotosError:
                pass
        now = utc_now()
        account.connection_state = "disconnected"
        account.account_subject = None
        account.account_email = None
        account.account_display_name = None
        account.account_picture_url = None
        account.access_token = None
        account.refresh_token = None
        account.scope = ""
        account.access_token_expires_at = None
        account.request_id = None
        account.device_id = None
        account.device_display_name = None
        account.settings_uri = None
        account.media_sources_set = False
        account.device_created_at = None
        account.last_device_poll_at = None
        account.disconnected_at = now
        account.current_error = ""
        account.updated_at = now
        self.repo.upsert_account(account)
        self.repo.cancel_active_auth_flows()
        return self.get_status()

    def mark_sync_requested(self) -> None:
        account = self._get_or_create_account()
        account.last_sync_requested_at = utc_now()
        account.updated_at = account.last_sync_requested_at
        self.repo.upsert_account(account)

    def run_sync(self, *, trigger: str) -> GooglePhotosSyncRun:
        account = self._get_or_create_account()
        started_at = utc_now()
        sync_run = GooglePhotosSyncRun(
            id=f"provider-sync-{uuid4().hex[:12]}",
            provider_name=PROVIDER_NAME,
            trigger=trigger,
            status="running",
            message="Google Photos sync in progress",
            error_message="",
            warning_messages=[],
            discovered_count=0,
            imported_count=0,
            duplicate_count=0,
            skipped_count=0,
            error_count=0,
            started_at=started_at,
        )
        self.repo.create_sync_run(sync_run)
        account.last_sync_requested_at = started_at
        account.updated_at = started_at
        self.repo.upsert_account(account)

        try:
            self._ensure_configured()
            if account.connection_state != "connected" or not account.request_id:
                sync_run.status = "skipped"
                sync_run.message = "Google Photos is not connected"
                sync_run.completed_at = utc_now()
                self.repo.update_sync_run(sync_run)
                return sync_run

            account = self._ensure_access_token(account)
            device_payload = self.client_factory().get_device(access_token=account.access_token or "", device_id=account.device_id or "")
            self._apply_device_payload(account, device_payload, poll_at=utc_now())
            account.updated_at = utc_now()
            self.repo.upsert_account(account)
            media_sources = self.repo.list_media_sources()
            if not account.media_sources_set or not media_sources:
                sync_run.status = "completed"
                sync_run.message = "No Google Photos media sources have been selected yet"
                sync_run.warning_messages = ["Open the Google Photos settings URI and choose media sources before syncing."]
                sync_run.completed_at = utc_now()
                self.repo.update_sync_run(sync_run)
                return sync_run

            stats = self._sync_selected_media_sources(account, media_sources)
            sync_run.discovered_count = stats.discovered_count
            sync_run.imported_count = stats.imported_count
            sync_run.duplicate_count = stats.duplicate_count
            sync_run.skipped_count = stats.skipped_count
            sync_run.error_count = stats.error_count
            sync_run.warning_messages = stats.warnings
            sync_run.status = "completed_with_errors" if stats.error_count else "completed"
            sync_run.message = (
                f"Synced {stats.imported_count} new assets, {stats.duplicate_count} duplicates, "
                f"{stats.skipped_count} skipped, {stats.error_count} errors"
            )
            sync_run.completed_at = utc_now()
            self.repo.update_sync_run(sync_run)
            account.current_error = ""
            account.last_completed_sync_at = sync_run.completed_at
            account.updated_at = sync_run.completed_at or account.updated_at
            self.repo.upsert_account(account)
            self.source_repo.touch_last_scan(GOOGLE_PHOTOS_SOURCE_ID, sync_run.completed_at or started_at)
            self.source_repo.touch_last_import(GOOGLE_PHOTOS_SOURCE_ID, sync_run.completed_at or started_at)
            return sync_run
        except Exception as exc:
            sync_run.status = "failed"
            sync_run.error_message = str(exc)
            sync_run.message = "Google Photos sync failed"
            sync_run.completed_at = utc_now()
            self.repo.update_sync_run(sync_run)
            account.current_error = str(exc)
            account.updated_at = sync_run.completed_at or account.updated_at
            self.repo.upsert_account(account)
            return sync_run

    def _sync_selected_media_sources(
        self,
        account: GooglePhotosAccount,
        media_sources: list[GooglePhotosMediaSource],
    ) -> GooglePhotosSyncStats:
        client = self.client_factory()
        stats = GooglePhotosSyncStats()
        remote_items: dict[str, GooglePhotosRemoteMediaItem] = {}
        remote_sources: dict[str, set[str]] = defaultdict(set)

        for media_source in media_sources:
            if not media_source.is_selected:
                continue
            if media_source.media_source_id == HIGHLIGHTS_MEDIA_SOURCE_ID:
                stats.warnings.append(
                    "Google Photos 'Highlights' is selected, but the Ambient API does not allow per-source enumeration for it."
                )
                continue
            page_token: str | None = None
            while True:
                items, next_page_token = client.list_media_items(
                    access_token=account.access_token or "",
                    device_id=account.device_id or "",
                    media_source_id=media_source.media_source_id,
                    page_token=page_token,
                    page_size=100,
                )
                for item in items:
                    remote_items[item.id] = item
                    remote_sources[item.id].add(media_source.media_source_id)
                if not next_page_token or next_page_token == page_token:
                    break
                page_token = next_page_token

        stats.discovered_count = len(remote_items)
        for remote_media_id, remote_item in remote_items.items():
            if not remote_item.mime_type.startswith("image/"):
                stats.skipped_count += 1
                stats.warnings.append(f"Skipped unsupported Google media item {remote_media_id} ({remote_item.mime_type}).")
                continue
            staging_suffix = self._guess_extension(remote_item.mime_type)
            staging_path = settings.google_photos_download_staging_dir / f"{remote_media_id}{staging_suffix}"
            try:
                media_bytes = client.download_media(access_token=account.access_token or "", base_url=remote_item.base_url)
                staging_path.parent.mkdir(parents=True, exist_ok=True)
                staging_path.write_bytes(media_bytes)
                result = self.asset_ingestion.ingest_file(
                    source_id=GOOGLE_PHOTOS_SOURCE_ID,
                    collection_ids=[GOOGLE_PHOTOS_COLLECTION_ID],
                    source_path=staging_path,
                    imported_from_path=f"google-photos://mediaItems/{remote_media_id}",
                    original_filename=f"{remote_media_id}{staging_suffix}",
                    metadata={
                        "provider": PROVIDER_NAME,
                        "google_media_id": remote_media_id,
                        "google_create_time": remote_item.create_time,
                        "google_media_sources": sorted(remote_sources[remote_media_id]),
                    },
                )
                if result.created:
                    stats.imported_count += 1
                else:
                    stats.duplicate_count += 1
                existing_mapping = self.repo.get_provider_asset(remote_media_id)
                first_synced_at = existing_mapping.first_synced_at if existing_mapping else utc_now()
                seen_at = utc_now()
                self.repo.upsert_provider_asset(
                    GooglePhotosProviderAsset(
                        id=existing_mapping.id if existing_mapping else f"provider-asset-{uuid4().hex[:12]}",
                        provider_name=PROVIDER_NAME,
                        remote_media_id=remote_media_id,
                        local_asset_id=result.asset.id,
                        mime_type=remote_item.mime_type,
                        width=remote_item.width,
                        height=remote_item.height,
                        create_time=remote_item.create_time,
                        imported_from_path=f"google-photos://mediaItems/{remote_media_id}",
                        remote_base_url=remote_item.base_url,
                        cached_original_path=result.asset.local_original_path,
                        checksum_sha256=result.checksum_sha256,
                        metadata_json=json_dumps(
                            {
                                "provider": PROVIDER_NAME,
                                "google_media_id": remote_media_id,
                                "media_source_ids": sorted(remote_sources[remote_media_id]),
                            }
                        ),
                        first_synced_at=first_synced_at,
                        last_synced_at=seen_at,
                        last_seen_at=seen_at,
                        is_active=True,
                        media_source_ids=sorted(remote_sources[remote_media_id]),
                    )
                )
            except Exception as exc:
                stats.error_count += 1
                stats.warnings.append(f"Failed to sync Google media item {remote_media_id}: {exc}")
            finally:
                staging_path.unlink(missing_ok=True)
        return stats

    def _refresh_device_state(self, account: GooglePhotosAccount, *, force: bool) -> GooglePhotosAccount:
        if not account.device_id:
            return account
        if not force and account.last_device_poll_at:
            last_polled_at = self._parse_timestamp(account.last_device_poll_at)
            if self._utc_now() < last_polled_at + timedelta(seconds=max(1, account.device_poll_interval_seconds)):
                return account
        account = self._ensure_access_token(account)
        device_payload = self.client_factory().get_device(access_token=account.access_token or "", device_id=account.device_id)
        self._apply_device_payload(account, device_payload, poll_at=utc_now())
        account.updated_at = utc_now()
        return self.repo.upsert_account(account)

    def _ensure_access_token(self, account: GooglePhotosAccount) -> GooglePhotosAccount:
        if not account.refresh_token and account.access_token and account.access_token_expires_at:
            if self._parse_timestamp(account.access_token_expires_at) > self._utc_now() + timedelta(seconds=60):
                return account
        if account.access_token and account.access_token_expires_at:
            if self._parse_timestamp(account.access_token_expires_at) > self._utc_now() + timedelta(seconds=60):
                return account
        if not account.refresh_token:
            raise GooglePhotosConfigurationError("Google Photos access token is unavailable and no refresh token is stored")
        token_payload = self.client_factory().refresh_access_token(account.refresh_token)
        account.access_token = str(token_payload.get("access_token") or "")
        account.scope = str(token_payload.get("scope") or account.scope)
        expires_in = int(token_payload.get("expires_in", 3600) or 3600)
        account.access_token_expires_at = (self._utc_now() + timedelta(seconds=expires_in)).isoformat()
        account.updated_at = utc_now()
        return self.repo.upsert_account(account)

    def _apply_device_payload(self, account: GooglePhotosAccount, payload: dict[str, Any], *, poll_at: str) -> None:
        account.device_id = self._optional_str(payload.get("id")) or account.device_id
        account.device_display_name = self._optional_str(payload.get("displayName")) or account.device_display_name
        account.settings_uri = self._optional_str(payload.get("settingsUri"))
        account.media_sources_set = bool(payload.get("mediaSourcesSet", False))
        polling_config = payload.get("pollingConfig") if isinstance(payload.get("pollingConfig"), dict) else {}
        account.device_poll_interval_seconds = parse_duration_seconds(self._optional_str(polling_config.get("pollInterval")), default=30)
        account.device_created_at = self._optional_str(payload.get("createTime")) or account.device_created_at
        account.last_device_poll_at = poll_at
        media_sources = self._media_sources_from_payload(payload.get("mediaSources"))
        self.repo.replace_media_sources(media_sources)

    def _media_sources_from_payload(self, payload: object) -> list[GooglePhotosMediaSource]:
        now = utc_now()
        media_sources: list[GooglePhotosMediaSource] = []
        if not isinstance(payload, list):
            return media_sources
        for item in payload:
            if not isinstance(item, dict):
                continue
            media_source_id = self._optional_str(item.get("id"))
            display_name = self._optional_str(item.get("displayName"))
            if not media_source_id or not display_name:
                continue
            media_sources.append(
                GooglePhotosMediaSource(
                    id=f"provider-media-source-{media_source_id}",
                    provider_name=PROVIDER_NAME,
                    media_source_id=media_source_id,
                    display_name=display_name,
                    is_selected=True,
                    last_seen_at=now,
                    created_at=now,
                    updated_at=now,
                )
            )
        return media_sources

    def _get_or_create_account(self) -> GooglePhotosAccount:
        account = self.repo.get_account()
        if account is not None:
            return account
        account = self.repo.create_default_account()
        return self.repo.upsert_account(account)

    @staticmethod
    def _optional_str(value: object) -> str | None:
        if value is None:
            return None
        text = str(value)
        return text if text else None

    @staticmethod
    def _parse_timestamp(value: str) -> datetime:
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=UTC)
        return parsed

    @staticmethod
    def _utc_now() -> datetime:
        return datetime.now(UTC)

    @staticmethod
    def _guess_extension(mime_type: str) -> str:
        guessed = mimetypes.guess_extension(mime_type, strict=False)
        if guessed == ".jpe":
            return ".jpg"
        return guessed or ".jpg"

    @staticmethod
    def _ensure_configured() -> None:
        if settings.google_photos_configured:
            return
        raise GooglePhotosConfigurationError("Google Photos OAuth client ID/secret are not configured")

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class GooglePhotosAuthFlow:
    id: str
    provider_name: str
    status: str
    request_id: str
    device_display_name: str
    device_code: str
    user_code: str
    verification_uri: str
    verification_uri_complete: str | None
    interval_seconds: int
    expires_at: str
    error_message: str
    created_at: str
    updated_at: str
    last_polled_at: str | None = None
    next_poll_at: str | None = None
    completed_at: str | None = None


@dataclass(slots=True)
class GooglePhotosAccount:
    id: str
    provider_name: str
    connection_state: str
    account_subject: str | None
    account_email: str | None
    account_display_name: str | None
    account_picture_url: str | None
    access_token: str | None
    refresh_token: str | None
    scope: str
    access_token_expires_at: str | None
    request_id: str | None
    device_id: str | None
    device_display_name: str | None
    settings_uri: str | None
    media_sources_set: bool
    device_poll_interval_seconds: int
    device_created_at: str | None
    last_device_poll_at: str | None
    connected_at: str | None
    disconnected_at: str | None
    last_sync_requested_at: str | None
    last_completed_sync_at: str | None
    current_error: str
    created_at: str
    updated_at: str


@dataclass(slots=True)
class GooglePhotosMediaSource:
    id: str
    provider_name: str
    media_source_id: str
    display_name: str
    is_selected: bool
    last_seen_at: str
    created_at: str
    updated_at: str


@dataclass(slots=True)
class GooglePhotosSyncRun:
    id: str
    provider_name: str
    trigger: str
    status: str
    message: str
    error_message: str
    warning_messages: list[str]
    discovered_count: int
    imported_count: int
    duplicate_count: int
    skipped_count: int
    error_count: int
    started_at: str
    completed_at: str | None = None


@dataclass(slots=True)
class GooglePhotosProviderAsset:
    id: str
    provider_name: str
    remote_media_id: str
    local_asset_id: str | None
    mime_type: str
    width: int
    height: int
    create_time: str | None
    imported_from_path: str
    remote_base_url: str
    cached_original_path: str | None
    checksum_sha256: str | None
    metadata_json: str
    first_synced_at: str
    last_synced_at: str
    last_seen_at: str
    is_active: bool
    media_source_ids: list[str] = field(default_factory=list)


@dataclass(slots=True)
class GooglePhotosRemoteMediaItem:
    id: str
    create_time: str | None
    base_url: str
    mime_type: str
    width: int
    height: int

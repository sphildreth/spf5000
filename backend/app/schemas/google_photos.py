from __future__ import annotations

from dataclasses import asdict

from pydantic import BaseModel, Field

from app.providers.google_photos.models import (
    GooglePhotosAccount,
    GooglePhotosAuthFlow,
    GooglePhotosMediaSource,
    GooglePhotosSyncRun,
)


class GooglePhotosConnectStartRequest(BaseModel):
    device_display_name: str | None = Field(default=None, min_length=1, max_length=100)


class GooglePhotosConnectPollRequest(BaseModel):
    flow_id: str | None = None


class GooglePhotosAccountSummaryResponse(BaseModel):
    subject: str | None = None
    email: str | None = None
    display_name: str | None = None
    picture_url: str | None = None
    connected_at: str | None = None

    @classmethod
    def from_domain(cls, account: GooglePhotosAccount) -> "GooglePhotosAccountSummaryResponse":
        return cls(
            subject=account.account_subject,
            email=account.account_email,
            display_name=account.account_display_name,
            picture_url=account.account_picture_url,
            connected_at=account.connected_at,
        )


class GooglePhotosAuthFlowResponse(BaseModel):
    id: str
    status: str
    request_id: str
    device_display_name: str
    user_code: str
    verification_uri: str
    verification_uri_complete: str | None = None
    interval_seconds: int
    expires_at: str
    last_polled_at: str | None = None
    next_poll_at: str | None = None
    error_message: str = ""

    @classmethod
    def from_domain(cls, flow: GooglePhotosAuthFlow) -> "GooglePhotosAuthFlowResponse":
        return cls(
            id=flow.id,
            status=flow.status,
            request_id=flow.request_id,
            device_display_name=flow.device_display_name,
            user_code=flow.user_code,
            verification_uri=flow.verification_uri,
            verification_uri_complete=flow.verification_uri_complete,
            interval_seconds=flow.interval_seconds,
            expires_at=flow.expires_at,
            last_polled_at=flow.last_polled_at,
            next_poll_at=flow.next_poll_at,
            error_message=flow.error_message,
        )


class GooglePhotosMediaSourceResponse(BaseModel):
    id: str
    display_name: str
    is_selected: bool
    last_seen_at: str

    @classmethod
    def from_domain(cls, media_source: GooglePhotosMediaSource) -> "GooglePhotosMediaSourceResponse":
        return cls(
            id=media_source.media_source_id,
            display_name=media_source.display_name,
            is_selected=media_source.is_selected,
            last_seen_at=media_source.last_seen_at,
        )


class GooglePhotosSyncRunResponse(BaseModel):
    id: str
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

    @classmethod
    def from_domain(cls, sync_run: GooglePhotosSyncRun) -> "GooglePhotosSyncRunResponse":
        return cls(**asdict(sync_run))


class GooglePhotosDeviceResponse(BaseModel):
    request_id: str | None = None
    device_id: str | None = None
    display_name: str | None = None
    settings_uri: str | None = None
    media_sources_set: bool
    poll_interval_seconds: int
    device_created_at: str | None = None
    last_polled_at: str | None = None


class GooglePhotosStatusResponse(BaseModel):
    provider: str
    provider_display_name: str
    available: bool
    configured: bool
    sync_cadence_seconds: int
    connection_state: str
    auth_flow: GooglePhotosAuthFlowResponse | None = None
    linked_account: GooglePhotosAccountSummaryResponse | None = None
    device: GooglePhotosDeviceResponse | None = None
    selected_media_sources: list[GooglePhotosMediaSourceResponse]
    latest_sync_run: GooglePhotosSyncRunResponse | None = None
    cached_asset_count: int
    current_error: str | None = None
    warnings: list[str]


class GooglePhotosSyncRequestResponse(BaseModel):
    queued: bool
    already_queued: bool
    trigger: str
    status: GooglePhotosStatusResponse

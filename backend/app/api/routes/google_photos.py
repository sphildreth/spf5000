from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, status

from app.providers.google_photos.errors import GooglePhotosError
from app.schemas.google_photos import (
    GooglePhotosAccountSummaryResponse,
    GooglePhotosAuthFlowResponse,
    GooglePhotosConnectPollRequest,
    GooglePhotosConnectStartRequest,
    GooglePhotosDeviceResponse,
    GooglePhotosMediaSourceResponse,
    GooglePhotosStatusResponse,
    GooglePhotosSyncRequestResponse,
    GooglePhotosSyncRunResponse,
)
from app.services.google_photos_service import GooglePhotosService

router = APIRouter()


def _service() -> GooglePhotosService:
    return GooglePhotosService()


def _status_response(payload: dict[str, object]) -> GooglePhotosStatusResponse:
    auth_flow = payload.get("auth_flow")
    linked_account = payload.get("linked_account")
    latest_sync_run = payload.get("latest_sync_run")
    device_payload = payload.get("device")
    media_sources = payload.get("selected_media_sources") or []
    return GooglePhotosStatusResponse(
        provider=str(payload["provider"]),
        provider_display_name=str(payload["provider_display_name"]),
        available=bool(payload["available"]),
        configured=bool(payload["configured"]),
        sync_cadence_seconds=int(payload["sync_cadence_seconds"]),
        connection_state=str(payload["connection_state"]),
        auth_flow=None if auth_flow is None else GooglePhotosAuthFlowResponse.from_domain(auth_flow),
        linked_account=None
        if linked_account is None
        else GooglePhotosAccountSummaryResponse(
            subject=linked_account.get("subject"),
            email=linked_account.get("email"),
            display_name=linked_account.get("display_name"),
            picture_url=linked_account.get("picture_url"),
            connected_at=linked_account.get("connected_at"),
        ),
        device=None
        if device_payload is None
        else GooglePhotosDeviceResponse(
            request_id=device_payload.get("request_id"),
            device_id=device_payload.get("device_id"),
            display_name=device_payload.get("display_name"),
            settings_uri=device_payload.get("settings_uri"),
            media_sources_set=bool(device_payload.get("media_sources_set", False)),
            poll_interval_seconds=int(device_payload.get("poll_interval_seconds") or 30),
            device_created_at=device_payload.get("device_created_at"),
            last_polled_at=device_payload.get("last_polled_at"),
        ),
        selected_media_sources=[GooglePhotosMediaSourceResponse.from_domain(item) for item in media_sources],
        latest_sync_run=None if latest_sync_run is None else GooglePhotosSyncRunResponse.from_domain(latest_sync_run),
        cached_asset_count=int(payload["cached_asset_count"]),
        current_error=None if payload.get("current_error") is None else str(payload["current_error"]),
        warnings=[str(item) for item in payload.get("warnings", [])],
    )


@router.get("/status", response_model=GooglePhotosStatusResponse)
def google_photos_status() -> GooglePhotosStatusResponse:
    return _status_response(_service().get_status())


@router.post("/connect/start", response_model=GooglePhotosStatusResponse)
def google_photos_connect_start(request: GooglePhotosConnectStartRequest) -> GooglePhotosStatusResponse:
    try:
        return _status_response(_service().start_connect(device_display_name=request.device_display_name))
    except (ValueError, GooglePhotosError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/connect/poll", response_model=GooglePhotosStatusResponse)
def google_photos_connect_poll(request: GooglePhotosConnectPollRequest) -> GooglePhotosStatusResponse:
    try:
        return _status_response(_service().poll_connect(flow_id=request.flow_id))
    except (ValueError, GooglePhotosError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/disconnect", response_model=GooglePhotosStatusResponse)
def google_photos_disconnect() -> GooglePhotosStatusResponse:
    return _status_response(_service().disconnect())


@router.post("/sync", response_model=GooglePhotosSyncRequestResponse)
def google_photos_sync(request: Request) -> GooglePhotosSyncRequestResponse:
    coordinator = getattr(request.app.state, "google_photos_sync_coordinator", None)
    if coordinator is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Google Photos sync coordinator is unavailable")
    service = _service()
    service.mark_sync_requested()
    queued, already_queued = coordinator.request_sync("manual")
    return GooglePhotosSyncRequestResponse(
        queued=queued,
        already_queued=already_queued,
        trigger="manual",
        status=_status_response(service.get_status()),
    )

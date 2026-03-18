from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status

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


def get_google_photos_service() -> GooglePhotosService:
    return GooglePhotosService()


def _status_response(payload: dict[str, object]) -> GooglePhotosStatusResponse:
    auth_flow = payload.get("auth_flow")
    account_data = payload.get("linked_account")
    latest_sync_run = payload.get("latest_sync_run")
    device_payload = payload.get("device")
    media_sources = payload.get("selected_media_sources") or []
    auth_flow_response = (
        None
        if auth_flow is None
        else GooglePhotosAuthFlowResponse.from_domain(auth_flow)
    )
    account_response = (
        None
        if account_data is None
        else GooglePhotosAccountSummaryResponse(
            subject=account_data.get("subject"),
            email=account_data.get("email"),
            display_name=account_data.get("display_name"),
            picture_url=account_data.get("picture_url"),
            connected_at=account_data.get("connected_at"),
        )
    )
    warnings = [str(item) for item in payload.get("warnings", [])]
    current_error = payload.get("current_error")
    return GooglePhotosStatusResponse(
        provider=str(payload["provider"]),
        provider_display_name=str(payload["provider_display_name"]),
        available=bool(payload["available"]),
        configured=bool(payload["configured"]),
        provider_available=bool(payload["available"]),
        provider_configured=bool(payload["configured"]),
        sync_cadence_seconds=int(payload["sync_cadence_seconds"]),
        connection_state=str(payload["connection_state"]),
        pending_auth=auth_flow_response,
        account=account_response,
        device=None
        if device_payload is None
        else GooglePhotosDeviceResponse(
            request_id=device_payload.get("request_id"),
            device_id=device_payload.get("device_id"),
            display_name=device_payload.get("display_name"),
            settings_uri=device_payload.get("settings_uri"),
            media_sources_set=bool(device_payload.get("media_sources_set", False)),
            poll_interval_seconds=int(
                device_payload.get("poll_interval_seconds") or 30
            ),
            device_created_at=device_payload.get("device_created_at"),
            last_polled_at=device_payload.get("last_polled_at"),
            selected_media_sources=[
                GooglePhotosMediaSourceResponse.from_domain(item)
                for item in media_sources
            ],
        ),
        selected_media_sources=[
            GooglePhotosMediaSourceResponse.from_domain(item) for item in media_sources
        ],
        latest_sync_run=None
        if latest_sync_run is None
        else GooglePhotosSyncRunResponse.from_domain(latest_sync_run),
        cached_asset_count=int(payload["cached_asset_count"]),
        error=None if current_error is None else str(current_error),
        warnings=warnings,
        warning=warnings[0] if warnings else None,
        last_successful_sync_at=(
            None
            if latest_sync_run is None or latest_sync_run.status == "failed"
            else latest_sync_run.completed_at
        ),
    )


@router.get("/status", response_model=GooglePhotosStatusResponse)
def google_photos_status(
    svc: GooglePhotosService = Depends(get_google_photos_service),
) -> GooglePhotosStatusResponse:
    return _status_response(svc.get_status())


@router.post("/connect/start", response_model=GooglePhotosStatusResponse)
def google_photos_connect_start(
    request: GooglePhotosConnectStartRequest,
    svc: GooglePhotosService = Depends(get_google_photos_service),
) -> GooglePhotosStatusResponse:
    try:
        return _status_response(
            svc.start_connect(device_display_name=request.device_display_name)
        )
    except (ValueError, GooglePhotosError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc


@router.post("/connect/poll", response_model=GooglePhotosStatusResponse)
def google_photos_connect_poll(
    request: GooglePhotosConnectPollRequest,
    svc: GooglePhotosService = Depends(get_google_photos_service),
) -> GooglePhotosStatusResponse:
    try:
        return _status_response(svc.poll_connect(flow_id=request.flow_id))
    except (ValueError, GooglePhotosError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc


@router.post("/disconnect", response_model=GooglePhotosStatusResponse)
def google_photos_disconnect(
    svc: GooglePhotosService = Depends(get_google_photos_service),
) -> GooglePhotosStatusResponse:
    return _status_response(svc.disconnect())


@router.post("/sync", response_model=GooglePhotosSyncRequestResponse)
def google_photos_sync(
    request: Request,
    svc: GooglePhotosService = Depends(get_google_photos_service),
) -> GooglePhotosSyncRequestResponse:
    coordinator = getattr(request.app.state, "google_photos_sync_coordinator", None)
    if coordinator is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google Photos sync coordinator is unavailable",
        )
    svc.mark_sync_requested()
    queued, already_queued = coordinator.request_sync("manual")
    return GooglePhotosSyncRequestResponse(
        queued=queued,
        already_queued=already_queued,
        trigger="manual",
        status=_status_response(svc.get_status()),
    )

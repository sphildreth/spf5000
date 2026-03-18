from __future__ import annotations

import threading
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import quote

import httpx

from app.core.config import settings
from app.providers.google_photos.errors import (
    GooglePhotosApiError,
    GooglePhotosAuthorizationDenied,
    GooglePhotosAuthorizationExpired,
    GooglePhotosAuthorizationPending,
    GooglePhotosConfigurationError,
    GooglePhotosSlowDown,
)
from app.providers.google_photos.models import GooglePhotosRemoteMediaItem
from app.providers.google_photos.oauth import build_device_flow_state

OAUTH_DEVICE_CODE_URL = "https://oauth2.googleapis.com/device/code"
OAUTH_TOKEN_URL = "https://oauth2.googleapis.com/token"
OPENID_USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"
AMBIENT_API_BASE_URL = "https://photosambient.googleapis.com/v1"
MEDIA_ITEMS_SCOPE = "https://www.googleapis.com/auth/photosambient.mediaitems"
PROFILE_SCOPES = "openid email profile"
DEFAULT_SCOPE = f"{PROFILE_SCOPES} {MEDIA_ITEMS_SCOPE}"

_default_timeout = httpx.Timeout(30.0, connect=10.0)
_client_lock = threading.Lock()
_shared_client: httpx.Client | None = None


def _get_shared_client() -> httpx.Client:
    global _shared_client
    with _client_lock:
        if _shared_client is None:
            _shared_client = httpx.Client(
                timeout=_default_timeout, follow_redirects=True
            )
        return _shared_client


class GooglePhotosClient:
    def __init__(self, timeout_seconds: float = 30.0) -> None:
        self.timeout_seconds = timeout_seconds

    @property
    def scope(self) -> str:
        return DEFAULT_SCOPE

    def start_device_flow(
        self, *, request_id: str, display_name: str
    ) -> dict[str, Any]:
        self._ensure_configured()
        payload = {
            "client_id": settings.google_photos_client_id,
            "scope": self.scope,
            "state": build_device_flow_state(
                request_id=request_id, display_name=display_name
            ),
        }
        response = self._post_form(OAUTH_DEVICE_CODE_URL, payload)
        expires_in = int(response.get("expires_in", 1800) or 1800)
        return {
            "device_code": str(response["device_code"]),
            "user_code": str(response["user_code"]),
            "verification_uri": str(
                response.get("verification_uri")
                or response.get("verification_url")
                or ""
            ),
            "verification_uri_complete": response.get("verification_uri_complete"),
            "interval_seconds": int(response.get("interval", 5) or 5),
            "expires_at": (
                datetime.now(UTC) + timedelta(seconds=expires_in)
            ).isoformat(),
        }

    def poll_device_flow(self, *, device_code: str) -> dict[str, Any]:
        self._ensure_configured()
        payload = {
            "client_id": settings.google_photos_client_id,
            "client_secret": settings.google_photos_client_secret,
            "device_code": device_code,
            "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
        }
        try:
            return self._post_form(OAUTH_TOKEN_URL, payload)
        except GooglePhotosApiError as exc:
            error = self._extract_error(exc.payload)
            if error == "authorization_pending":
                raise GooglePhotosAuthorizationPending() from exc
            if error == "slow_down":
                raise GooglePhotosSlowDown(10) from exc
            if error == "access_denied":
                raise GooglePhotosAuthorizationDenied(
                    "Google Photos access was denied"
                ) from exc
            if error == "expired_token":
                raise GooglePhotosAuthorizationExpired(
                    "The Google Photos approval code expired"
                ) from exc
            raise

    def refresh_access_token(self, refresh_token: str) -> dict[str, Any]:
        self._ensure_configured()
        payload = {
            "client_id": settings.google_photos_client_id,
            "client_secret": settings.google_photos_client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }
        return self._post_form(OAUTH_TOKEN_URL, payload)

    def get_userinfo(self, access_token: str) -> dict[str, Any]:
        return self._get_json(
            OPENID_USERINFO_URL, headers=self._auth_headers(access_token)
        )

    def create_device(
        self, *, access_token: str, request_id: str, display_name: str
    ) -> dict[str, Any]:
        return self._post_json(
            f"{AMBIENT_API_BASE_URL}/devices?requestId={quote(request_id, safe='')}",
            {"displayName": display_name},
            headers=self._auth_headers(access_token),
        )

    def get_device(self, *, access_token: str, device_id: str) -> dict[str, Any]:
        return self._get_json(
            f"{AMBIENT_API_BASE_URL}/devices/{quote(device_id, safe='')}",
            headers=self._auth_headers(access_token),
        )

    def delete_device(
        self, *, access_token: str, device_id: str | None, request_id: str | None
    ) -> None:
        identifier = device_id or request_id
        if not identifier:
            return
        self._delete(
            f"{AMBIENT_API_BASE_URL}/devices/{quote(identifier, safe='')}",
            headers=self._auth_headers(access_token),
        )

    def list_media_items(
        self,
        *,
        access_token: str,
        device_id: str,
        media_source_id: str | None = None,
        page_token: str | None = None,
        page_size: int = 100,
    ) -> tuple[list[GooglePhotosRemoteMediaItem], str | None]:
        params: dict[str, str | int] = {
            "deviceId": device_id,
            "pageSize": max(1, min(page_size, 100)),
        }
        if media_source_id:
            params["mediaSourceId"] = media_source_id
        if page_token:
            params["pageToken"] = page_token
        response = self._get_json(
            f"{AMBIENT_API_BASE_URL}/mediaItems",
            headers=self._auth_headers(access_token),
            params=params,
        )
        items: list[GooglePhotosRemoteMediaItem] = []
        for item in response.get("mediaItems", []) or []:
            if not isinstance(item, dict):
                continue
            media_file = (
                item.get("mediaFile", {})
                if isinstance(item.get("mediaFile"), dict)
                else {}
            )
            metadata = (
                media_file.get("mediaFileMetadata", {})
                if isinstance(media_file.get("mediaFileMetadata"), dict)
                else {}
            )
            items.append(
                GooglePhotosRemoteMediaItem(
                    id=str(item.get("id", "")),
                    create_time=None
                    if item.get("createTime") is None
                    else str(item.get("createTime")),
                    base_url=str(media_file.get("baseUrl", "")),
                    mime_type=str(
                        media_file.get("mimeType", "application/octet-stream")
                    ),
                    width=int(metadata.get("width") or 0),
                    height=int(metadata.get("height") or 0),
                )
            )
        next_page_token = response.get("nextPageToken")
        return items, None if next_page_token is None else str(next_page_token)

    def download_media_to_file(
        self, *, access_token: str, base_url: str, dest_path: Any
    ) -> None:
        url = f"{base_url}=d"
        client = _get_shared_client()
        with client.stream(
            "GET", url, headers=self._auth_headers(access_token)
        ) as response:
            if response.status_code >= 400:
                response.read()
                raise GooglePhotosApiError(
                    f"Google Photos media download failed with status {response.status_code}",
                    status_code=response.status_code,
                    payload=self._decode_payload(response),
                )
            with open(dest_path, "wb") as f:
                for chunk in response.iter_bytes(chunk_size=8192 * 8):
                    f.write(chunk)

    def download_media(self, *, access_token: str, base_url: str) -> bytes:
        url = f"{base_url}=d"
        client = _get_shared_client()
        response = client.get(url, headers=self._auth_headers(access_token))
        if response.status_code >= 400:
            raise GooglePhotosApiError(
                f"Google Photos media download failed with status {response.status_code}",
                status_code=response.status_code,
                payload=self._decode_payload(response),
            )
        return response.content

    def _post_form(self, url: str, payload: dict[str, Any]) -> dict[str, Any]:
        client = _get_shared_client()
        response = client.post(url, data=payload)
        return self._decode_json_response(response)

    def _post_json(
        self, url: str, payload: dict[str, Any], *, headers: dict[str, str]
    ) -> dict[str, Any]:
        client = _get_shared_client()
        response = client.post(url, json=payload, headers=headers)
        return self._decode_json_response(response)

    def _get_json(
        self, url: str, *, headers: dict[str, str], params: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        client = _get_shared_client()
        response = client.get(url, headers=headers, params=params)
        return self._decode_json_response(response)

    def _delete(self, url: str, *, headers: dict[str, str]) -> None:
        client = _get_shared_client()
        response = client.delete(url, headers=headers)
        if response.status_code >= 400:
            raise GooglePhotosApiError(
                f"Google Photos delete failed with status {response.status_code}",
                status_code=response.status_code,
                payload=self._decode_payload(response),
            )

    def _decode_json_response(self, response: httpx.Response) -> dict[str, Any]:
        if response.status_code >= 400:
            raise GooglePhotosApiError(
                self._extract_message(response),
                status_code=response.status_code,
                payload=self._decode_payload(response),
            )
        payload = self._decode_payload(response)
        if isinstance(payload, dict):
            return payload
        raise GooglePhotosApiError(
            "Google Photos returned a non-object response",
            status_code=response.status_code,
            payload=payload,
        )

    @staticmethod
    def _decode_payload(response: httpx.Response) -> object:
        try:
            return response.json()
        except ValueError:
            return response.text

    @staticmethod
    def _extract_error(payload: object | None) -> str | None:
        if isinstance(payload, dict):
            raw = payload.get("error")
            if isinstance(raw, str):
                return raw
        return None

    @staticmethod
    def _extract_message(response: httpx.Response) -> str:
        payload = GooglePhotosClient._decode_payload(response)
        if isinstance(payload, dict):
            if isinstance(payload.get("error_description"), str):
                return str(payload["error_description"])
            if isinstance(payload.get("error"), str):
                return str(payload["error"])
            if isinstance(payload.get("message"), str):
                return str(payload["message"])
            nested = payload.get("error")
            if isinstance(nested, dict) and isinstance(nested.get("message"), str):
                return str(nested["message"])
        return f"Google Photos request failed with status {response.status_code}"

    @staticmethod
    def _auth_headers(access_token: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {access_token}"}

    @staticmethod
    def _ensure_configured() -> None:
        if settings.google_photos_configured:
            return
        raise GooglePhotosConfigurationError(
            "Google Photos OAuth client ID/secret are not configured"
        )

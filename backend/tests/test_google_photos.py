from __future__ import annotations

from io import BytesIO

from PIL import Image

from app.core.config import settings
from app.providers.google_photos.models import GooglePhotosRemoteMediaItem
from app.repositories.google_photos_repository import GooglePhotosRepository
from app.services.google_photos_service import GooglePhotosService


class FakeSyncCoordinator:
    def __init__(self) -> None:
        self.requests: list[str] = []

    def request_sync(self, trigger: str = "manual") -> tuple[bool, bool]:
        self.requests.append(trigger)
        return True, False


class FakeGooglePhotosClient:
    def __init__(self) -> None:
        self.poll_attempts = 0
        self.deleted_device_ids: list[str] = []
        self.device = {
            "id": "device-1",
            "displayName": "SPF5000 Test Frame",
            "settingsUri": "https://photos.google.test/settings/device-1",
            "createTime": "2026-03-16T00:00:00Z",
            "pollingConfig": {"pollInterval": "7s"},
            "mediaSourcesSet": False,
            "mediaSources": [],
        }
        self.media_items_by_source = {
            "album-1": [
                GooglePhotosRemoteMediaItem(
                    id="remote-1",
                    create_time="2026-03-15T00:00:00Z",
                    base_url="https://photos.google.test/media/remote-1",
                    mime_type="image/jpeg",
                    width=1200,
                    height=800,
                )
            ]
        }

    @property
    def scope(self) -> str:
        return "openid email profile https://www.googleapis.com/auth/photosambient.mediaitems"

    def start_device_flow(
        self, *, request_id: str, display_name: str
    ) -> dict[str, object]:
        self.device["displayName"] = display_name
        return {
            "device_code": f"device-code-{request_id}",
            "user_code": "ABCD-EFGH",
            "verification_uri": "https://www.google.com/device",
            "verification_uri_complete": "https://www.google.com/device?user_code=ABCD-EFGH",
            "interval_seconds": 1,
            "expires_at": "2099-01-01T00:00:00+00:00",
        }

    def poll_device_flow(self, *, device_code: str) -> dict[str, object]:
        self.poll_attempts += 1
        if self.poll_attempts == 1:
            from app.providers.google_photos.errors import (
                GooglePhotosAuthorizationPending,
            )

            raise GooglePhotosAuthorizationPending()
        return {
            "access_token": "access-token-1",
            "refresh_token": "refresh-token-1",
            "expires_in": 3600,
            "scope": self.scope,
        }

    def refresh_access_token(self, refresh_token: str) -> dict[str, object]:
        return {
            "access_token": "access-token-refreshed",
            "expires_in": 3600,
            "scope": self.scope,
        }

    def get_userinfo(self, access_token: str) -> dict[str, object]:
        return {
            "sub": "subject-123",
            "email": "user@example.com",
            "name": "Google User",
            "picture": "https://example.com/picture.jpg",
        }

    def create_device(
        self, *, access_token: str, request_id: str, display_name: str
    ) -> dict[str, object]:
        self.device["displayName"] = display_name
        return dict(self.device)

    def get_device(self, *, access_token: str, device_id: str) -> dict[str, object]:
        return dict(self.device)

    def delete_device(
        self, *, access_token: str, device_id: str | None, request_id: str | None
    ) -> None:
        self.deleted_device_ids.append(device_id or request_id or "")

    def list_media_items(
        self,
        *,
        access_token: str,
        device_id: str,
        media_source_id: str | None = None,
        page_token: str | None = None,
        page_size: int = 100,
    ) -> tuple[list[object], str | None]:
        del access_token, device_id, page_token, page_size
        return list(self.media_items_by_source.get(media_source_id or "", [])), None

    def download_media(self, *, access_token: str, base_url: str) -> bytes:
        del access_token, base_url
        image = Image.new("RGB", (1200, 800), color=(255, 0, 0))
        handle = BytesIO()
        image.save(handle, format="JPEG")
        return handle.getvalue()


def _configure_google_settings(monkeypatch) -> None:
    monkeypatch.setattr(settings, "google_photos_client_id", "test-client-id")
    monkeypatch.setattr(settings, "google_photos_client_secret", "test-client-secret")
    monkeypatch.setattr(
        settings, "google_photos_provider_display_name", "Google Photos"
    )
    monkeypatch.setattr(settings, "google_photos_sync_cadence_seconds", 3600)


def _install_fake_client(monkeypatch, fake_client: FakeGooglePhotosClient) -> None:
    monkeypatch.setattr(
        GooglePhotosService, "client_factory", staticmethod(lambda: fake_client)
    )


def _expire_active_flow() -> None:
    repo = GooglePhotosRepository()
    flow = repo.get_latest_auth_flow(include_completed=False)
    assert flow is not None
    flow.next_poll_at = "2000-01-01T00:00:00+00:00"
    repo.update_auth_flow(flow)


def test_google_photos_status_and_device_flow_routes(test_client, monkeypatch) -> None:
    fake_client = FakeGooglePhotosClient()
    _configure_google_settings(monkeypatch)
    _install_fake_client(monkeypatch, fake_client)

    status_response = test_client.get("/api/google-photos/status")
    assert status_response.status_code == 200
    status_body = status_response.json()
    assert status_body["provider"] == "google_photos"
    assert status_body["configured"] is True
    assert status_body["connection_state"] == "disconnected"

    start_response = test_client.post(
        "/api/google-photos/connect/start",
        json={"device_display_name": "SPF5000 Test Frame"},
    )
    assert start_response.status_code == 200
    start_body = start_response.json()
    assert start_body["connection_state"] == "awaiting_authorization"
    assert start_body["pending_auth"]["user_code"] == "ABCD-EFGH"

    _expire_active_flow()
    pending_response = test_client.post("/api/google-photos/connect/poll", json={})
    assert pending_response.status_code == 200
    pending_body = pending_response.json()
    assert pending_body["connection_state"] == "awaiting_authorization"
    assert pending_body["pending_auth"]["status"] == "polling"

    _expire_active_flow()
    fake_client.device["mediaSourcesSet"] = True
    fake_client.device["mediaSources"] = [
        {"id": "album-1", "displayName": "Vacation"},
        {"id": "highlights", "displayName": "Highlights"},
    ]
    connected_response = test_client.post("/api/google-photos/connect/poll", json={})
    assert connected_response.status_code == 200
    connected_body = connected_response.json()
    assert connected_body["connection_state"] == "connected"
    assert connected_body["account"]["email"] == "user@example.com"
    assert (
        connected_body["device"]["settings_uri"]
        == "https://photos.google.test/settings/device-1"
    )
    assert {item["id"] for item in connected_body["selected_media_sources"]} == {
        "album-1",
        "highlights",
    }
    assert any("Highlights" in warning for warning in connected_body["warnings"])


def test_google_photos_sync_and_disconnect_preserve_cached_assets(
    test_client, monkeypatch
) -> None:
    fake_client = FakeGooglePhotosClient()
    fake_client.poll_attempts = 1
    fake_client.device["mediaSourcesSet"] = True
    fake_client.device["mediaSources"] = [
        {"id": "album-1", "displayName": "Vacation"},
        {"id": "highlights", "displayName": "Highlights"},
    ]
    _configure_google_settings(monkeypatch)
    _install_fake_client(monkeypatch, fake_client)

    service = GooglePhotosService()
    service.start_connect(device_display_name="SPF5000 Test Frame")
    _expire_active_flow()
    service.poll_connect()

    sync_run = service.run_sync(trigger="manual")
    assert sync_run.status == "completed"
    assert sync_run.imported_count == 1
    assert sync_run.duplicate_count == 0
    assert any("Highlights" in warning for warning in sync_run.warning_messages)

    assets_response = test_client.get("/api/assets")
    assert assets_response.status_code == 200
    assets = assets_response.json()
    assert len(assets) == 1

    disconnect_response = test_client.post("/api/google-photos/disconnect")
    assert disconnect_response.status_code == 200
    disconnect_body = disconnect_response.json()
    assert disconnect_body["connection_state"] == "disconnected"
    assert disconnect_body["cached_asset_count"] == 1
    assert any(
        "Cached Google Photos assets" in warning
        for warning in disconnect_body["warnings"]
    )
    assert fake_client.deleted_device_ids == ["device-1"]


def test_google_photos_sync_route_queues_manual_sync(test_client, monkeypatch) -> None:
    fake_client = FakeGooglePhotosClient()
    _configure_google_settings(monkeypatch)
    _install_fake_client(monkeypatch, fake_client)

    coordinator = FakeSyncCoordinator()
    test_client.app.state.google_photos_sync_coordinator = coordinator

    response = test_client.post("/api/google-photos/sync")
    assert response.status_code == 200
    body = response.json()
    assert body["queued"] is True
    assert body["already_queued"] is False
    assert coordinator.requests == ["manual"]

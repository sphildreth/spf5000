from __future__ import annotations

from datetime import datetime, timezone

from fastapi.testclient import TestClient


def test_post_display_refresh_triggers_playlist_reload(test_client: TestClient) -> None:
    since = datetime.now(timezone.utc).isoformat()

    before_response = test_client.get("/api/display/new-assets/count", params={"since": since})
    assert before_response.status_code == 200
    assert before_response.json()["new_assets_count"] == 0

    refresh_response = test_client.post("/api/display/refresh")
    assert refresh_response.status_code == 200
    body = refresh_response.json()
    assert body["refreshed"] is True
    assert isinstance(body["invalidated_at"], str)
    assert body["invalidated_at"]

    after_response = test_client.get("/api/display/new-assets/count", params={"since": since})
    assert after_response.status_code == 200
    assert after_response.json()["new_assets_count"] >= 1

    cleared_response = test_client.get(
        "/api/display/new-assets/count",
        params={"since": body["invalidated_at"]},
    )
    assert cleared_response.status_code == 200
    assert cleared_response.json()["new_assets_count"] == 0

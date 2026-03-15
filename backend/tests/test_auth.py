"""Tests covering setup, authentication, session management, and route protection."""
from __future__ import annotations

from pathlib import Path

from PIL import Image
from fastapi.testclient import TestClient


def _write_sample_image(path: Path, color: tuple[int, int, int]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    image = Image.new("RGB", (800, 600), color=color)
    image.save(path, format="JPEG")


def _setup_payload(
    username: str = "admin",
    password: str = "strongpass1",
    confirm_password: str | None = None,
) -> dict[str, str]:
    password_confirmation = password if confirm_password is None else confirm_password
    return {
        "username": username,
        "password": password,
        "confirm_password": password_confirmation,
    }


_PROTECTED_ROUTES: list[tuple[str, str]] = [
    ("GET", "/api/status"),
    ("GET", "/api/system/status"),
    ("GET", "/api/settings"),
    ("GET", "/api/collections"),
    ("GET", "/api/assets"),
    ("GET", "/api/sources"),
    ("POST", "/api/import/local/scan"),
    ("POST", "/api/import/local/run"),
    ("GET", "/api/display/config"),
    ("PUT", "/api/display/config"),
]


def test_fresh_install_session_state_reports_not_bootstrapped(fresh_client: TestClient) -> None:
    response = fresh_client.get("/api/auth/session")

    assert response.status_code == 200
    assert response.json() == {
        "auth_available": True,
        "bootstrapped": False,
        "authenticated": False,
        "user": None,
    }


def test_health_always_public(fresh_client: TestClient) -> None:
    response = fresh_client.get("/api/health")

    assert response.status_code == 200
    assert response.json()["ok"] is True


def test_protected_admin_routes_return_401_before_setup(fresh_client: TestClient) -> None:
    for method, path in _PROTECTED_ROUTES:
        response = fresh_client.request(method, path)
        assert response.status_code == 401, (
            f"Expected 401 for {method} {path}, got {response.status_code}: {response.text}"
        )


def test_setup_creates_admin_and_authenticates_session(fresh_client: TestClient) -> None:
    response = fresh_client.post("/api/setup", json=_setup_payload())

    assert response.status_code == 200
    assert response.json() == {
        "auth_available": True,
        "bootstrapped": True,
        "authenticated": True,
        "user": {"username": "admin"},
    }

    session_response = fresh_client.get("/api/auth/session")
    assert session_response.status_code == 200
    assert session_response.json() == {
        "auth_available": True,
        "bootstrapped": True,
        "authenticated": True,
        "user": {"username": "admin"},
    }

    assert fresh_client.get("/api/status").status_code == 200


def test_setup_becomes_unavailable_after_bootstrap(fresh_client: TestClient) -> None:
    first_response = fresh_client.post("/api/setup", json=_setup_payload())
    assert first_response.status_code == 200

    second_response = fresh_client.post(
        "/api/setup",
        json=_setup_payload(username="other-admin", password="strongpass2"),
    )
    assert second_response.status_code == 409


def test_setup_validates_password_confirmation(fresh_client: TestClient) -> None:
    response = fresh_client.post(
        "/api/setup",
        json=_setup_payload(password="strongpass1", confirm_password="differentpass1"),
    )

    assert response.status_code == 422


def test_setup_validates_password_length(fresh_client: TestClient) -> None:
    response = fresh_client.post("/api/setup", json=_setup_payload(password="short"))

    assert response.status_code == 422


def test_login_requires_bootstrap(fresh_client: TestClient) -> None:
    response = fresh_client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "anything"},
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "System setup must be completed before login"


def test_login_with_valid_credentials(fresh_client: TestClient) -> None:
    fresh_client.post("/api/setup", json=_setup_payload())
    fresh_client.post("/api/auth/logout")

    response = fresh_client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "strongpass1"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "auth_available": True,
        "bootstrapped": True,
        "authenticated": True,
        "user": {"username": "admin"},
    }


def test_login_with_bad_password_returns_401(fresh_client: TestClient) -> None:
    fresh_client.post("/api/setup", json=_setup_payload())
    fresh_client.post("/api/auth/logout")

    response = fresh_client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "wrongpassword"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid username or password"


def test_logout_clears_session(fresh_client: TestClient) -> None:
    fresh_client.post("/api/setup", json=_setup_payload())
    assert fresh_client.get("/api/status").status_code == 200

    logout_response = fresh_client.post("/api/auth/logout")
    assert logout_response.status_code == 200
    assert logout_response.json() == {
        "auth_available": True,
        "bootstrapped": True,
        "authenticated": False,
        "user": None,
    }

    assert fresh_client.get("/api/auth/session").json() == {
        "auth_available": True,
        "bootstrapped": True,
        "authenticated": False,
        "user": None,
    }
    assert fresh_client.get("/api/status").status_code == 401


def test_public_display_playlist_and_asset_variant_remain_accessible_without_auth(
    fresh_client: TestClient,
) -> None:
    setup_response = fresh_client.post("/api/setup", json=_setup_payload())
    assert setup_response.status_code == 200

    sources = fresh_client.get("/api/sources").json()
    import_dir = Path(sources[0]["import_path"])
    _write_sample_image(import_dir / "alpha.jpg", (200, 100, 50))
    _write_sample_image(import_dir / "beta.jpg", (50, 100, 200))

    import_response = fresh_client.post(
        "/api/import/local/run",
        json={
            "source_id": sources[0]["id"],
            "collection_id": "default-collection",
            "max_samples": 5,
        },
    )
    assert import_response.status_code == 200
    assert import_response.json()["imported_count"] == 2

    assets = fresh_client.get("/api/assets").json()
    assert len(assets) == 2
    variant_url = assets[0]["display_url"]

    logout_response = fresh_client.post("/api/auth/logout")
    assert logout_response.status_code == 200

    playlist_response = fresh_client.get("/api/display/playlist")
    assert playlist_response.status_code == 200
    assert playlist_response.json()["collection_id"] == "default-collection"
    assert len(playlist_response.json()["items"]) == 2

    variant_response = fresh_client.get(variant_url)
    assert variant_response.status_code == 200
    assert variant_response.headers["content-type"].startswith("image/jpeg")

    assert fresh_client.get("/api/assets").status_code == 401

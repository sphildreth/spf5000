"""Tests for rate limiting functionality."""

from __future__ import annotations

import os
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi.testclient import TestClient


def test_rate_limiting_disabled_by_env_var(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verify rate limiting is disabled when SPF5000_RATE_LIMIT=false."""
    from app.core.config import settings
    from app.main import create_app

    data_dir = tmp_path / "data"
    cache_dir = tmp_path / "cache"
    log_dir = tmp_path / "logs"

    monkeypatch.setattr(settings, "data_dir", data_dir)
    monkeypatch.setattr(settings, "cache_dir", cache_dir)
    monkeypatch.setattr(settings, "log_dir", log_dir)
    monkeypatch.setattr(settings, "database_path", data_dir / "spf5000.ddb")
    monkeypatch.setattr(settings, "frontend_dist_dir", tmp_path / "frontend-dist")
    monkeypatch.setattr(
        settings, "legacy_frontend_dist_dir", tmp_path / "frontend-dist-legacy"
    )
    monkeypatch.setattr(settings, "session_secret", "test-secret-32bytes!!!!")
    monkeypatch.setenv("SPF5000_RATE_LIMIT", "false")

    app = create_app()
    with TestClient(app, raise_server_exceptions=True) as client:
        resp = client.post(
            "/api/setup",
            json={
                "username": "testadmin",
                "password": "testpassword1",
                "confirm_password": "testpassword1",
            },
        )
        assert resp.status_code == 200


def test_rate_limiting_check_function_respects_env(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verify check_rate_limit respects SPF5000_RATE_LIMIT env var."""
    from app.api.rate_limit import check_rate_limit

    monkeypatch.setenv("SPF5000_RATE_LIMIT", "false")
    assert check_rate_limit("127.0.0.1", "1/minute") is True

    monkeypatch.setenv("SPF5000_RATE_LIMIT", "true")
    assert check_rate_limit("192.168.1.100", "1/minute") is True
    assert check_rate_limit("192.168.1.100", "1/minute") is False


def test_rate_limit_prunes_stale_ip_entries(monkeypatch: pytest.MonkeyPatch) -> None:
    """Expired IP buckets should not remain in the in-memory rate-limit map forever."""
    from app.api import rate_limit

    rate_limit._request_counts.clear()
    rate_limit._last_global_prune_at = 0.0
    rate_limit._largest_tracked_window_seconds = 0.0
    monkeypatch.setenv("SPF5000_RATE_LIMIT", "true")

    timestamps = iter([0.0, 61.0])
    monkeypatch.setattr(rate_limit.time, "time", lambda: next(timestamps))

    assert rate_limit.check_rate_limit("10.0.0.1", "1/minute") is True
    assert "10.0.0.1|1/minute" in rate_limit._request_counts

    assert rate_limit.check_rate_limit("10.0.0.2", "1/minute") is True
    assert "10.0.0.1|1/minute" not in rate_limit._request_counts
    assert set(rate_limit._request_counts) == {"10.0.0.2|1/minute"}

    rate_limit._request_counts.clear()
    rate_limit._last_global_prune_at = 0.0
    rate_limit._largest_tracked_window_seconds = 0.0


def test_rate_limiting_login_endpoint(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verify login endpoint rate limits when enabled."""
    from app.core.config import settings
    from app.main import create_app

    data_dir = tmp_path / "data"
    cache_dir = tmp_path / "cache"
    log_dir = tmp_path / "logs"

    monkeypatch.setattr(settings, "data_dir", data_dir)
    monkeypatch.setattr(settings, "cache_dir", cache_dir)
    monkeypatch.setattr(settings, "log_dir", log_dir)
    monkeypatch.setattr(settings, "database_path", data_dir / "spf5000.ddb")
    monkeypatch.setattr(settings, "frontend_dist_dir", tmp_path / "frontend-dist")
    monkeypatch.setattr(
        settings, "legacy_frontend_dist_dir", tmp_path / "frontend-dist-legacy"
    )
    monkeypatch.setattr(settings, "session_secret", "test-secret-32bytes!!!!")
    monkeypatch.setenv("SPF5000_RATE_LIMIT", "true")

    app = create_app()
    with TestClient(app, raise_server_exceptions=True) as client:
        resp = client.post(
            "/api/setup",
            json={
                "username": "testadmin",
                "password": "testpassword1",
                "confirm_password": "testpassword1",
            },
        )
        assert resp.status_code == 200

        # The login budget is 10/minute and is independent of the setup call above, so the
        # eleventh attempt is the first one that must be refused.
        resp2: Any = None
        for _ in range(12):
            resp2 = client.post(
                "/api/auth/login",
                json={
                    "username": "testadmin",
                    "password": "wrongpassword",
                },
            )
            if resp2.status_code == 429:
                break
        assert resp2.status_code == 429


def test_config_key_enables_and_disables_limiting(monkeypatch: pytest.MonkeyPatch) -> None:
    """`[security] rate_limit_enabled` must actually gate limiting; the env var overrides it."""
    from app.api import rate_limit
    from app.core.config import settings

    monkeypatch.delenv("SPF5000_RATE_LIMIT", raising=False)

    monkeypatch.setattr(settings, "rate_limit_enabled", False)
    assert rate_limit.is_rate_limit_enabled() is False

    monkeypatch.setattr(settings, "rate_limit_enabled", True)
    assert rate_limit.is_rate_limit_enabled() is True

    monkeypatch.setenv("SPF5000_RATE_LIMIT", "false")
    assert rate_limit.is_rate_limit_enabled() is False


def test_each_endpoint_has_its_own_budget(monkeypatch: pytest.MonkeyPatch) -> None:
    """One endpoint's limit must not consume another endpoint's budget for the same caller."""
    from app.api import rate_limit

    rate_limit._request_counts.clear()
    monkeypatch.setenv("SPF5000_RATE_LIMIT", "true")

    assert rate_limit.check_rate_limit("10.0.0.5", "1/minute") is True
    assert rate_limit.check_rate_limit("10.0.0.5", "1/minute") is False
    # Same caller, different limit string: unaffected by the exhausted budget above.
    assert rate_limit.check_rate_limit("10.0.0.5", "5/minute") is True

    rate_limit._request_counts.clear()


def test_client_ip_ignores_forwarded_header_without_a_trusted_proxy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """SPF5000 terminates its own HTTP, so X-Forwarded-For is only honoured on request."""
    from app.api.rate_limit import client_ip

    request = SimpleNamespace(
        headers={"X-Forwarded-For": "203.0.113.9"},
        client=SimpleNamespace(host="192.0.2.7"),
    )

    monkeypatch.delenv("SPF5000_TRUST_PROXY", raising=False)
    assert client_ip(request) == "192.0.2.7"

    monkeypatch.setenv("SPF5000_TRUST_PROXY", "true")
    assert client_ip(request) == "203.0.113.9"


def test_public_display_playlist_is_rate_limited(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The public display endpoints are reachable without auth, so they must be bounded."""
    from app.api import rate_limit
    from app.core.config import settings
    from app.main import create_app

    data_dir = tmp_path / "data"
    monkeypatch.setattr(settings, "data_dir", data_dir)
    monkeypatch.setattr(settings, "cache_dir", tmp_path / "cache")
    monkeypatch.setattr(settings, "log_dir", tmp_path / "logs")
    monkeypatch.setattr(settings, "database_path", data_dir / "spf5000.ddb")
    monkeypatch.setattr(settings, "frontend_dist_dir", tmp_path / "frontend-dist")
    monkeypatch.setattr(
        settings, "legacy_frontend_dist_dir", tmp_path / "frontend-dist-legacy"
    )
    monkeypatch.setattr(settings, "session_secret", "test-secret-32bytes!!!!")
    monkeypatch.setenv("SPF5000_RATE_LIMIT", "true")
    rate_limit._request_counts.clear()

    statuses: list[int] = []
    with TestClient(create_app(), raise_server_exceptions=True) as client:
        for _ in range(125):
            statuses.append(client.get("/api/display/playlist").status_code)

    assert statuses[:120] == [200] * 120
    assert set(statuses[120:]) == {429}

    rate_limit._request_counts.clear()

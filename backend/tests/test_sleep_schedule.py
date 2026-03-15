"""Tests for the sleep schedule domain logic and API endpoints."""
from __future__ import annotations

import pytest

from app.models.sleep_schedule import (
    SleepSchedule,
    is_in_sleep_window,
    normalize_hhmm,
    normalize_sleep_schedule,
    parse_hhmm,
)


# ---------------------------------------------------------------------------
# parse_hhmm unit tests
# ---------------------------------------------------------------------------


def test_parse_hhmm_valid() -> None:
    assert parse_hhmm("00:00") == (0, 0)
    assert parse_hhmm("23:59") == (23, 59)
    assert parse_hhmm("08:30") == (8, 30)


def test_normalize_hhmm_returns_canonical_value() -> None:
    assert normalize_hhmm("08:30") == "08:30"


@pytest.mark.parametrize(
    "bad_value",
    ["24:00", "23:60", "9:00", "08:5", "8am", "", "::"],
)
def test_parse_hhmm_invalid(bad_value: str) -> None:
    with pytest.raises(ValueError):
        parse_hhmm(bad_value)


# ---------------------------------------------------------------------------
# is_in_sleep_window — schedule disabled
# ---------------------------------------------------------------------------


def test_sleep_window_disabled_always_false() -> None:
    schedule = SleepSchedule(sleep_schedule_enabled=False, sleep_start_local_time="22:00", sleep_end_local_time="08:00")
    for hhmm in ("22:00", "23:00", "00:00", "07:59", "08:00", "12:00"):
        assert is_in_sleep_window(hhmm, schedule) is False, f"Expected False at {hhmm} when disabled"


def test_normalize_sleep_schedule_rejects_equal_start_end_when_enabled() -> None:
    with pytest.raises(ValueError):
        normalize_sleep_schedule(
            SleepSchedule(
                sleep_schedule_enabled=True,
                sleep_start_local_time="08:00",
                sleep_end_local_time="08:00",
            )
        )


# ---------------------------------------------------------------------------
# is_in_sleep_window — overnight window (22:00 → 08:00)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "current_time,expected",
    [
        # boundary: start is inside
        ("22:00", True),
        # deep in overnight window
        ("23:30", True),
        ("00:00", True),
        ("03:45", True),
        ("07:59", True),
        # boundary: end is exclusive
        ("08:00", False),
        # middle of the day → awake
        ("12:00", False),
        ("21:59", False),
    ],
)
def test_sleep_window_overnight(current_time: str, expected: bool) -> None:
    schedule = SleepSchedule(sleep_schedule_enabled=True, sleep_start_local_time="22:00", sleep_end_local_time="08:00")
    assert is_in_sleep_window(current_time, schedule) is expected, (
        f"is_in_sleep_window({current_time!r}, overnight) expected {expected}"
    )


# ---------------------------------------------------------------------------
# is_in_sleep_window — same-day window (14:00 → 16:00)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "current_time,expected",
    [
        # boundary: start inside
        ("14:00", True),
        ("15:00", True),
        # boundary: end is exclusive
        ("16:00", False),
        # outside
        ("13:59", False),
        ("16:01", False),
        ("00:00", False),
        ("23:59", False),
    ],
)
def test_sleep_window_same_day(current_time: str, expected: bool) -> None:
    schedule = SleepSchedule(sleep_schedule_enabled=True, sleep_start_local_time="14:00", sleep_end_local_time="16:00")
    assert is_in_sleep_window(current_time, schedule) is expected, (
        f"is_in_sleep_window({current_time!r}, same-day) expected {expected}"
    )


# ---------------------------------------------------------------------------
# is_in_sleep_window — edge: start just past midnight
# ---------------------------------------------------------------------------


def test_sleep_window_midnight_start() -> None:
    """00:00–06:00 — no midnight crossover, just an early-morning same-day window."""
    schedule = SleepSchedule(sleep_schedule_enabled=True, sleep_start_local_time="00:00", sleep_end_local_time="06:00")
    assert is_in_sleep_window("00:00", schedule) is True
    assert is_in_sleep_window("05:59", schedule) is True
    assert is_in_sleep_window("06:00", schedule) is False
    assert is_in_sleep_window("06:01", schedule) is False
    assert is_in_sleep_window("23:59", schedule) is False


# ---------------------------------------------------------------------------
# API: GET /settings/sleep-schedule
# ---------------------------------------------------------------------------


def test_get_sleep_schedule_defaults(test_client) -> None:
    response = test_client.get("/api/settings/sleep-schedule")
    assert response.status_code == 200
    body = response.json()
    assert body["sleep_schedule_enabled"] is False
    assert body["sleep_start_local_time"] == "22:00"
    assert body["sleep_end_local_time"] == "08:00"


# ---------------------------------------------------------------------------
# API: PUT /settings/sleep-schedule — happy path
# ---------------------------------------------------------------------------


def test_update_sleep_schedule(test_client) -> None:
    payload = {
        "sleep_schedule_enabled": True,
        "sleep_start_local_time": "23:00",
        "sleep_end_local_time": "07:00",
    }
    put_response = test_client.put("/api/settings/sleep-schedule", json=payload)
    assert put_response.status_code == 200
    body = put_response.json()
    assert body["sleep_schedule_enabled"] is True
    assert body["sleep_start_local_time"] == "23:00"
    assert body["sleep_end_local_time"] == "07:00"

    # Verify GET returns the persisted value
    get_response = test_client.get("/api/settings/sleep-schedule")
    assert get_response.status_code == 200
    assert get_response.json() == body


# ---------------------------------------------------------------------------
# API: PUT /settings/sleep-schedule — validation errors
# ---------------------------------------------------------------------------


def test_update_sleep_schedule_rejects_equal_start_end_when_enabled(test_client) -> None:
    payload = {
        "sleep_schedule_enabled": True,
        "sleep_start_local_time": "08:00",
        "sleep_end_local_time": "08:00",
    }
    response = test_client.put("/api/settings/sleep-schedule", json=payload)
    assert response.status_code == 422
    body = response.json()
    # Error detail should mention equal times
    detail_str = str(body)
    assert "08:00" in detail_str


def test_update_sleep_schedule_allows_equal_start_end_when_disabled(test_client) -> None:
    """Identical start/end is valid when the schedule is disabled (it can't cause confusion)."""
    payload = {
        "sleep_schedule_enabled": False,
        "sleep_start_local_time": "12:00",
        "sleep_end_local_time": "12:00",
    }
    response = test_client.put("/api/settings/sleep-schedule", json=payload)
    assert response.status_code == 200


def test_update_sleep_schedule_rejects_bad_hhmm_format(test_client) -> None:
    payload = {
        "sleep_schedule_enabled": False,
        "sleep_start_local_time": "9am",
        "sleep_end_local_time": "08:00",
    }
    response = test_client.put("/api/settings/sleep-schedule", json=payload)
    assert response.status_code == 422


def test_update_sleep_schedule_rejects_out_of_range_time(test_client) -> None:
    payload = {
        "sleep_schedule_enabled": False,
        "sleep_start_local_time": "25:00",
        "sleep_end_local_time": "08:00",
    }
    response = test_client.put("/api/settings/sleep-schedule", json=payload)
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# API: sleep-schedule routes require authentication
# ---------------------------------------------------------------------------


def test_sleep_schedule_routes_require_auth(fresh_client) -> None:
    """Both GET and PUT must return 401 when the user is not authenticated."""
    from app.core.config import settings as app_settings

    # Bootstrap admin so auth is available (otherwise returns 503)
    fresh_client.post(
        "/api/setup",
        json={"username": "admin", "password": "strongpass1", "confirm_password": "strongpass1"},
    )
    fresh_client.post("/api/auth/logout")

    assert fresh_client.get("/api/settings/sleep-schedule").status_code == 401
    assert fresh_client.put("/api/settings/sleep-schedule", json={}).status_code == 401


# ---------------------------------------------------------------------------
# Display playlist includes sleep_schedule
# ---------------------------------------------------------------------------


def test_display_playlist_includes_sleep_schedule(test_client) -> None:
    playlist_response = test_client.get("/api/display/playlist")
    assert playlist_response.status_code == 200
    playlist = playlist_response.json()
    assert "sleep_schedule" in playlist
    ss = playlist["sleep_schedule"]
    assert "sleep_schedule_enabled" in ss
    assert "sleep_start_local_time" in ss
    assert "sleep_end_local_time" in ss


def test_display_playlist_sleep_schedule_reflects_update(test_client) -> None:
    """Updating the sleep schedule should be visible in the public playlist payload."""
    payload = {
        "sleep_schedule_enabled": True,
        "sleep_start_local_time": "21:30",
        "sleep_end_local_time": "06:30",
    }
    put_response = test_client.put("/api/settings/sleep-schedule", json=payload)
    assert put_response.status_code == 200

    playlist_response = test_client.get("/api/display/playlist")
    assert playlist_response.status_code == 200
    ss = playlist_response.json()["sleep_schedule"]
    assert ss["sleep_schedule_enabled"] is True
    assert ss["sleep_start_local_time"] == "21:30"
    assert ss["sleep_end_local_time"] == "06:30"

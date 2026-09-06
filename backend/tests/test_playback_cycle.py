"""Slideshow playback-cycle tests (ADR 0024).

These cover the "show all before repeating" promise, including the scenarios that previously
collapsed it: browser/kiosk restarts, and library changes that force the display to re-anchor.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Iterable

from fastapi.testclient import TestClient

from app.db.bootstrap import DEFAULT_COLLECTION_ID
from app.db.connection import get_connection
from app.services.display_service import (
    NEW_ASSET_HEAD_MIN_SLOTS,
    PLAYBACK_MODE_SEQUENTIAL,
    PLAYBACK_MODE_SHUFFLE_BAG,
    PLAYBACK_MODE_SHUFFLE_RANDOM,
    DisplayService,
)

ASSET_COUNT = 60
_STAMP = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _sequence(asset_id: str) -> int:
    return int(asset_id.removeprefix("asset-"))


def _insert_asset(asset_id: str) -> None:
    imported_at = (_STAMP + timedelta(minutes=_sequence(asset_id))).isoformat()
    with get_connection() as conn:
        conn.execute(
            """
            insert into assets (
                id, source_id, checksum_sha256, filename, original_filename, original_extension,
                mime_type, width, height, size_bytes, imported_from_path, local_original_path,
                metadata_json, created_at, updated_at, imported_at, is_active
            ) values (?, 'default-local-files', ?, ?, ?, '.jpg', 'image/jpeg', 1920, 1080, 100,
                      ?, ?, '{}', ?, ?, ?, 1)
            """,
            (
                asset_id,
                f"checksum-{asset_id}",
                f"{asset_id}.jpg",
                f"{asset_id}.jpg",
                f"/import/{asset_id}.jpg",
                f"/original/{asset_id}.jpg",
                imported_at,
                imported_at,
                imported_at,
            ),
        )
        conn.execute(
            """
            insert into collection_assets (collection_id, asset_id, sort_order, added_at)
            values (?, ?, 0, ?)
            """,
            (DEFAULT_COLLECTION_ID, asset_id, imported_at),
        )


def _seed(asset_count: int = ASSET_COUNT) -> list[str]:
    asset_ids = [f"asset-{index}" for index in range(asset_count)]
    for asset_id in asset_ids:
        _insert_asset(asset_id)
    return asset_ids


def _set_deactivated(asset_id: str) -> None:
    with get_connection() as conn:
        conn.execute("update assets set is_active = 0 where id = ?", (asset_id,))


def _upcoming(playlist) -> list[str]:
    return [item.asset_id for item in playlist.items][playlist.playback_position :]


def _play_until_repeat(
    svc: DisplayService,
    *,
    max_slides: int,
    already_shown: Iterable[str] = (),
) -> tuple[list[str], str | None]:
    """Play slides the way ``/display`` does and stop at the first repeat.

    Walks the served order forward from ``playback_position``, reports each committed photograph,
    and re-fetches at the end of a cycle so the backend deals the next pass. ``already_shown`` is
    the current pass tally as the viewer perceives it, which survives a restart, so a photograph
    shown before this call starts counts as a repeat.
    """
    seen = set(already_shown)
    shown: list[str] = []
    playlist = svc.get_playlist()
    index = playlist.playback_position

    while len(shown) < max_slides:
        if index >= len(playlist.items):
            playlist = svc.get_playlist()
            index = playlist.playback_position
            if not playlist.items:
                break
        asset_id = playlist.items[index].asset_id
        if asset_id in seen:
            return shown, asset_id
        seen.add(asset_id)
        shown.append(asset_id)
        svc.report_playback_position(asset_id, playlist.collection_id)
        index += 1
    return shown, None


def test_shuffle_bag_shows_every_asset_before_repeating(test_client: TestClient) -> None:
    _seed()
    svc = DisplayService()

    shown, repeat = _play_until_repeat(svc, max_slides=ASSET_COUNT * 4)

    assert repeat is not None, "harness never completed a pass, so the guarantee is untested"
    assert len(shown) == ASSET_COUNT
    assert len(set(shown)) == ASSET_COUNT


def test_cycle_survives_a_browser_or_kiosk_restart(test_client: TestClient) -> None:
    """A fresh display process, and a cleared backend cache, must resume the same pass."""
    _seed()
    svc = DisplayService()
    first = svc.get_playlist()
    assert first.playback_mode == PLAYBACK_MODE_SHUFFLE_BAG
    shown_before = [item.asset_id for item in first.items[:20]]

    for asset_id in shown_before:
        svc.report_playback_position(asset_id, first.collection_id)

    # The incognito kiosk reloads: no client state at all, and the backend playlist cache is gone.
    svc.refresh_playlist_cache()
    resumed = DisplayService().get_playlist()

    assert resumed.playback_cycle_id == first.playback_cycle_id
    assert resumed.playback_position == 20

    shown, repeat = _play_until_repeat(
        DisplayService(),
        max_slides=ASSET_COUNT * 2,
        already_shown=shown_before,
    )

    # The rest of the pass plays out untouched, and only then does the bag roll over.
    assert repeat is not None
    assert len(shown) == ASSET_COUNT - 20
    assert set(shown) == {item.asset_id for item in first.items[20:]}


def test_removing_the_shown_asset_does_not_restart_the_pass(test_client: TestClient) -> None:
    """The original defect: re-anchoring after the current photo left the playlist wiped progress."""
    _seed()
    svc = DisplayService()
    order = [item.asset_id for item in svc.get_playlist().items]

    for asset_id in order[:20]:
        svc.report_playback_position(asset_id, DEFAULT_COLLECTION_ID)

    # The photograph on screen disappears from the library, so /display re-anchors on its next poll.
    on_screen = order[19]
    _set_deactivated(on_screen)
    reanchored = svc.get_playlist()

    assert on_screen not in {item.asset_id for item in reanchored.items}
    # Re-anchoring resumes the pass: the one shown photograph drops out of the shown tally and the
    # 40 unseen ones stay queued ahead of the cursor.
    assert reanchored.playback_position == 19
    assert set(_upcoming(reanchored)) == set(order[20:])
    assert len(reanchored.items) == ASSET_COUNT - 1

    shown, repeat = _play_until_repeat(
        svc,
        max_slides=ASSET_COUNT * 4,
        already_shown=order[:19],  # order[19] was deactivated after being shown
    )

    assert repeat is not None
    assert len(shown) == ASSET_COUNT - 20
    assert set(shown) == set(order[20:])


def test_removing_an_unseen_asset_keeps_the_rest_queued(test_client: TestClient) -> None:
    _seed()
    svc = DisplayService()
    playlist = svc.get_playlist()
    order = [item.asset_id for item in playlist.items]

    for asset_id in order[:10]:
        svc.report_playback_position(asset_id, playlist.collection_id)
    _set_deactivated(order[29])

    refreshed = svc.get_playlist()
    assert refreshed.playback_position == 10
    assert set(_upcoming(refreshed)) == set(order[10:29]) | set(order[30:])


def test_new_assets_surface_within_a_few_slides(test_client: TestClient) -> None:
    _seed()
    svc = DisplayService()
    order = [item.asset_id for item in svc.get_playlist().items]
    for asset_id in order[:10]:
        svc.report_playback_position(asset_id, DEFAULT_COLLECTION_ID)

    fresh_ids = [f"asset-{ASSET_COUNT + offset}" for offset in range(3)]
    for asset_id in fresh_ids:
        _insert_asset(asset_id)

    upcoming = _upcoming(svc.get_playlist())
    for asset_id in fresh_ids:
        assert upcoming.index(asset_id) <= NEW_ASSET_HEAD_MIN_SLOTS + 3
    # Surfacing new work early must not duplicate anything already shown this pass.
    assert len(set(upcoming)) == len(upcoming)


def test_progress_never_moves_backwards(test_client: TestClient) -> None:
    _seed()
    svc = DisplayService()
    playlist = svc.get_playlist()
    order = [item.asset_id for item in playlist.items]

    svc.report_playback_position(order[9], playlist.collection_id)
    assert svc.get_playlist().playback_position == 10

    # A stale or replayed report for an earlier photograph is ignored.
    svc.report_playback_position(order[2], playlist.collection_id)
    assert svc.get_playlist().playback_position == 10

    svc.report_playback_position(order[9], playlist.collection_id)
    assert svc.get_playlist().playback_position == 10


def test_report_for_unknown_asset_is_a_noop(test_client: TestClient) -> None:
    _seed()
    svc = DisplayService()
    playlist = svc.get_playlist()

    assert svc.report_playback_position("not-an-asset", playlist.collection_id) is None
    assert svc.get_playlist().playback_position == 0


def test_sequential_mode_walks_newest_first_and_tracks_nothing(test_client: TestClient) -> None:
    asset_ids = _seed()
    svc = DisplayService()
    svc.update_config({"shuffle_enabled": False})

    playlist = svc.get_playlist()
    assert playlist.playback_mode == PLAYBACK_MODE_SEQUENTIAL
    assert playlist.playback_position == 0
    assert [item.asset_id for item in playlist.items] == list(reversed(asset_ids))
    assert (
        svc.report_playback_position(playlist.items[0].asset_id, playlist.collection_id) is None
    )


def test_disabling_the_bag_permits_repeats_within_a_pass(test_client: TestClient) -> None:
    _seed()
    svc = DisplayService()
    svc.update_config({"shuffle_bag_enabled": False})

    playlist = svc.get_playlist()
    assert playlist.playback_mode == PLAYBACK_MODE_SHUFFLE_RANDOM
    order = [item.asset_id for item in playlist.items]
    assert len(order) == ASSET_COUNT
    # Sampled with replacement, so a pass contains duplicates by design.
    assert len(set(order)) < ASSET_COUNT


def test_switching_modes_redeals_rather_than_resuming_a_stale_cycle(test_client: TestClient) -> None:
    _seed()
    svc = DisplayService()
    before = svc.get_playlist()
    svc.report_playback_position(before.items[3].asset_id, before.collection_id)

    svc.update_config({"shuffle_bag_enabled": False})
    after = svc.get_playlist()

    assert after.playback_mode == PLAYBACK_MODE_SHUFFLE_RANDOM
    assert after.playback_cycle_id != before.playback_cycle_id
    assert after.playback_position == 0


def test_progress_endpoint_is_public_and_advances_the_cursor(fresh_client: TestClient) -> None:
    _seed()
    svc = DisplayService()
    playlist = svc.get_playlist()

    response = fresh_client.post(
        "/api/display/playlist/progress",
        json={
            "asset_id": playlist.items[0].asset_id,
            "collection_id": playlist.collection_id,
        },
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["accepted"] is True
    assert body["playback_position"] == 1
    assert body["playback_cycle_id"] == playlist.playback_cycle_id
    assert svc.get_playlist().playback_position == 1


def test_progress_endpoint_rejects_empty_asset_id(fresh_client: TestClient) -> None:
    _seed()

    assert (
        fresh_client.post("/api/display/playlist/progress", json={"asset_id": ""}).status_code
        == 422
    )


def test_playlist_exposes_playback_fields(test_client: TestClient) -> None:
    _seed()

    body = test_client.get("/api/display/playlist").json()

    assert body["playback_mode"] == PLAYBACK_MODE_SHUFFLE_BAG
    assert body["playback_cycle_id"]
    assert body["playback_position"] == 0
    assert len(body["items"]) == ASSET_COUNT

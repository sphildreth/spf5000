from __future__ import annotations

from dataclasses import dataclass

from app.db.connection import get_connection, is_null_connection
from app.repositories.base import json_dumps, json_loads, row_to_dict, utc_now

# Playable scope key used when the display profile has no collection selected.
GLOBAL_PLAYBACK_KEY = "*global*"


@dataclass(slots=True)
class PlaybackCycle:
    """A server-owned slideshow cycle: a permutation plus the cursor into it (ADR 0024)."""

    collection_key: str
    mode: str
    cycle_id: str
    order: list[str]
    position: int


class PlaybackStateRepository:
    def get_cycle(self, collection_key: str) -> PlaybackCycle | None:
        with get_connection() as conn:
            if is_null_connection(conn):
                return None
            cursor = conn.execute(
                "select collection_key, mode, cycle_id, order_json, position from display_playback_state where collection_key = ?",
                (collection_key,),
            )
            row = row_to_dict(cursor, cursor.fetchone())
            if row is None:
                return None
            order = json_loads(str(row["order_json"] or ""), [])
            if not isinstance(order, list):
                return None
            return PlaybackCycle(
                collection_key=str(row["collection_key"]),
                mode=str(row["mode"] or ""),
                cycle_id=str(row["cycle_id"] or ""),
                order=[str(asset_id) for asset_id in order],
                position=max(0, int(row["position"] or 0)),
            )

    def save_cycle(self, cycle: PlaybackCycle) -> PlaybackCycle:
        now = utc_now()
        with get_connection() as conn:
            if is_null_connection(conn):
                return cycle
            conn.execute(
                """
                insert into display_playback_state (collection_key, mode, cycle_id, order_json, position, updated_at)
                values (?, ?, ?, ?, ?, ?)
                on conflict(collection_key) do update set
                    mode = excluded.mode,
                    cycle_id = excluded.cycle_id,
                    order_json = excluded.order_json,
                    position = excluded.position,
                    updated_at = excluded.updated_at
                """,
                (
                    cycle.collection_key,
                    cycle.mode,
                    cycle.cycle_id,
                    json_dumps(cycle.order),
                    cycle.position,
                    now,
                ),
            )
        return cycle

    def advance_to(self, collection_key: str, cycle_id: str, position: int) -> None:
        """Move the cursor forward for an existing cycle. Never moves backwards, never re-deals."""
        with get_connection() as conn:
            if is_null_connection(conn):
                return
            conn.execute(
                """
                update display_playback_state
                set position = ?, updated_at = ?
                where collection_key = ? and cycle_id = ? and position < ?
                """,
                (position, utc_now(), collection_key, cycle_id, position),
            )

    def delete_cycle(self, collection_key: str) -> None:
        with get_connection() as conn:
            if is_null_connection(conn):
                return
            conn.execute("delete from display_playback_state where collection_key = ?", (collection_key,))

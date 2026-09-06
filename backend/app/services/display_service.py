from __future__ import annotations

from collections import OrderedDict
from dataclasses import asdict, replace
from datetime import datetime, timezone
import hashlib
import json
import random
import threading
from uuid import uuid4

import structlog

from app.models.asset import AssetBackground
from app.models.display import DisplayPlaylist, DisplayProfile, PlaylistItem
from app.models.sleep_schedule import SleepSchedule
from app.repositories.asset_repository import AssetRepository
from app.repositories.collection_repository import CollectionRepository
from app.repositories.display_repository import DisplayRepository
from app.repositories.playback_state_repository import (
    GLOBAL_PLAYBACK_KEY,
    PlaybackCycle,
    PlaybackStateRepository,
)
from app.repositories.settings_repository import SettingsRepository
from app.services.background_service import (
    VALID_BACKGROUND_FILL_MODES,
    background_meta_from_dict,
)

LOGGER = structlog.get_logger(__name__)
_PLAYLIST_CACHE_MAX_ENTRIES = 4
_PLAYLIST_CACHE: OrderedDict[tuple[str, str], DisplayPlaylist] = OrderedDict()
_PLAYLIST_CACHE_INVALIDATED_AT: datetime | None = None
_PLAYLIST_CACHE_LOCK = threading.Lock()

# Slideshow ordering modes (ADR 0024).
PLAYBACK_MODE_SEQUENTIAL = "sequential"
PLAYBACK_MODE_SHUFFLE_BAG = "shuffle_bag"
PLAYBACK_MODE_SHUFFLE_RANDOM = "shuffle_random"

# Newly eligible photographs are inserted within this fraction of the remaining queue, with a slot
# floor, so fresh imports surface within a few minutes instead of waiting out a full cycle.
NEW_ASSET_HEAD_FRACTION = 10
NEW_ASSET_HEAD_MIN_SLOTS = 10


class DisplayService:
    def __init__(
        self,
        display_repo: DisplayRepository | None = None,
        asset_repo: AssetRepository | None = None,
        collection_repo: CollectionRepository | None = None,
        settings_repo: SettingsRepository | None = None,
        playback_repo: PlaybackStateRepository | None = None,
    ) -> None:
        self.display_repo = display_repo or DisplayRepository()
        self.asset_repo = asset_repo or AssetRepository()
        self.collection_repo = collection_repo or CollectionRepository()
        self.settings_repo = settings_repo or SettingsRepository()
        self.playback_repo = playback_repo or PlaybackStateRepository()

    def get_config(self) -> DisplayProfile:
        settings = self.settings_repo.get_settings()
        background_fill_mode = settings.background_fill_mode
        shuffle_bag_enabled = settings.shuffle_bag_enabled
        profile = self.display_repo.get_default_profile()
        if profile is None:
            return DisplayProfile(
                id=settings.active_display_profile_id,
                name="Default Display",
                selected_collection_id=settings.selected_collection_id,
                slideshow_interval_seconds=settings.slideshow_interval_seconds,
                transition_mode=settings.transition_mode,
                transition_duration_ms=settings.transition_duration_ms,
                fit_mode=settings.fit_mode,
                shuffle_enabled=settings.shuffle_enabled,
                idle_message="Add photos from the admin UI to begin playback.",
                refresh_interval_seconds=60,
                is_default=True,
                created_at="",
                updated_at="",
                background_fill_mode=settings.background_fill_mode,
                shuffle_bag_enabled=settings.shuffle_bag_enabled,
            )
        profile.background_fill_mode = background_fill_mode
        profile.shuffle_bag_enabled = shuffle_bag_enabled
        return profile

    @staticmethod
    def clear_runtime_cache() -> None:
        global _PLAYLIST_CACHE_INVALIDATED_AT
        with _PLAYLIST_CACHE_LOCK:
            _PLAYLIST_CACHE.clear()
            _PLAYLIST_CACHE_INVALIDATED_AT = None

    def update_config(self, updates: dict[str, object]) -> DisplayProfile:
        # Handle settings-backed display fields separately — persisted in settings, not display_profiles.
        if (
            "background_fill_mode" in updates
            and updates["background_fill_mode"] is not None
        ) or (
            "shuffle_bag_enabled" in updates
            and updates["shuffle_bag_enabled"] is not None
        ):
            frame_settings = self.settings_repo.get_settings()
            if (
                "background_fill_mode" in updates
                and updates["background_fill_mode"] is not None
            ):
                mode = str(updates["background_fill_mode"])
                if mode in VALID_BACKGROUND_FILL_MODES:
                    frame_settings.background_fill_mode = mode
            if (
                "shuffle_bag_enabled" in updates
                and updates["shuffle_bag_enabled"] is not None
            ):
                frame_settings.shuffle_bag_enabled = bool(
                    updates["shuffle_bag_enabled"]
                )
            self.settings_repo.update_settings(frame_settings)

        profile = self.get_config()
        for field_name in (
            "name",
            "selected_collection_id",
            "slideshow_interval_seconds",
            "transition_mode",
            "transition_duration_ms",
            "fit_mode",
            "shuffle_enabled",
            "idle_message",
            "refresh_interval_seconds",
        ):
            if field_name in updates and updates[field_name] is not None:
                setattr(profile, field_name, updates[field_name])
        updated_profile = self.display_repo.update_profile(profile)
        settings = self.settings_repo.get_settings()
        settings.slideshow_interval_seconds = updated_profile.slideshow_interval_seconds
        settings.transition_mode = updated_profile.transition_mode
        settings.transition_duration_ms = updated_profile.transition_duration_ms
        settings.fit_mode = updated_profile.fit_mode
        settings.shuffle_enabled = updated_profile.shuffle_enabled
        settings.selected_collection_id = updated_profile.selected_collection_id or ""
        settings.active_display_profile_id = updated_profile.id
        self.settings_repo.update_settings(settings)
        # Ensure settings-backed fields are fresh on the returned profile.
        refreshed_settings = self.settings_repo.get_settings()
        updated_profile.background_fill_mode = refreshed_settings.background_fill_mode
        updated_profile.shuffle_bag_enabled = refreshed_settings.shuffle_bag_enabled
        return updated_profile

    def get_playlist(self, collection_id: str | None = None) -> DisplayPlaylist:
        profile = self.get_config()
        resolved_collection_id = collection_id or profile.selected_collection_id
        collection = (
            self.collection_repo.get_collection(resolved_collection_id)
            if resolved_collection_id
            else None
        )
        sleep_schedule = self.settings_repo.get_sleep_schedule()
        assets = self.asset_repo.list_playlist_assets(collection_id=resolved_collection_id)

        # The backend owns what plays next (ADR 0024). Sequential mode walks the newest-first
        # listing; shuffle modes walk a persisted cycle so a pass survives reloads and restarts.
        mode = self._playback_mode(profile)
        playback_key = resolved_collection_id or GLOBAL_PLAYBACK_KEY
        cycle = self._resolve_playback_cycle(
            mode=mode,
            playback_key=playback_key,
            asset_ids=[asset.id for asset in assets],
        )

        playlist_revision = self._compute_playlist_revision(
            profile=profile,
            collection_id=resolved_collection_id,
            collection=collection,
            sleep_schedule=sleep_schedule,
            cycle=cycle,
        )
        cache_key = (playback_key, playlist_revision)
        cached = self._get_cached_playlist(cache_key)
        if cached is not None:
            # The revision pins the cycle and the eligible id set, so a cache hit has the same item
            # order; only the cursor moves between reads.
            return replace(cached, playback_position=cycle.position)

        assets_by_id = {asset.id: asset for asset in assets}
        items = []
        for asset_id in cycle.order:
            asset = assets_by_id.get(asset_id)
            if asset is None:
                continue
            background = self._background_from_metadata(asset.metadata_json)
            items.append(
                PlaylistItem(
                    asset_id=asset.id,
                    filename=asset.filename,
                    display_url=f"/api/assets/{asset.id}/variants/display",
                    thumbnail_url=f"/api/assets/{asset.id}/variants/thumbnail",
                    width=asset.width,
                    height=asset.height,
                    checksum_sha256=asset.checksum_sha256,
                    mime_type=asset.mime_type,
                    background=background,
                )
            )
        playlist = DisplayPlaylist(
            profile=profile,
            collection_id=resolved_collection_id,
            collection_name=None if collection is None else collection.name,
            shuffle_enabled=profile.shuffle_enabled,
            playlist_revision=playlist_revision,
            playback_mode=mode,
            playback_cycle_id=cycle.cycle_id,
            playback_position=cycle.position,
            background_fill_mode=profile.background_fill_mode,
            sleep_schedule=sleep_schedule,
            items=items,
        )
        self._store_cached_playlist(cache_key, playlist)
        return playlist

    def report_playback_position(
        self, asset_id: str, collection_id: str | None = None
    ) -> PlaybackCycle | None:
        """Advance the persisted cursor past ``asset_id`` after the display has shown it.

        Idempotent and forward-only within a cycle. Returns ``None`` when there is nothing to
        track, which the display treats as a no-op rather than an error.
        """
        profile = self.get_config()
        mode = self._playback_mode(profile)
        if mode == PLAYBACK_MODE_SEQUENTIAL:
            return None

        resolved_collection_id = collection_id or profile.selected_collection_id
        playback_key = resolved_collection_id or GLOBAL_PLAYBACK_KEY
        cycle = self.playback_repo.get_cycle(playback_key)
        if cycle is None or not cycle.order or cycle.mode != mode:
            return None
        try:
            index = cycle.order.index(asset_id)
        except ValueError:
            return None
        self.playback_repo.advance_to(playback_key, cycle.cycle_id, index + 1)
        return PlaybackCycle(
            collection_key=playback_key,
            mode=mode,
            cycle_id=cycle.cycle_id,
            order=cycle.order,
            position=max(cycle.position, index + 1),
        )

    @staticmethod
    def _playback_mode(profile: DisplayProfile) -> str:
        if not profile.shuffle_enabled:
            return PLAYBACK_MODE_SEQUENTIAL
        if profile.shuffle_bag_enabled:
            return PLAYBACK_MODE_SHUFFLE_BAG
        return PLAYBACK_MODE_SHUFFLE_RANDOM

    def _resolve_playback_cycle(
        self, *, mode: str, playback_key: str, asset_ids: list[str]
    ) -> PlaybackCycle:
        """Return the cycle to serve, reconciling it against the currently eligible assets.

        A partially completed pass is never discarded: removed photographs drop out and newly
        eligible ones are inserted near the head of the remaining queue.
        """
        if mode == PLAYBACK_MODE_SEQUENTIAL:
            return PlaybackCycle(
                collection_key=playback_key,
                mode=mode,
                cycle_id=PLAYBACK_MODE_SEQUENTIAL,
                order=list(asset_ids),
                position=0,
            )
        if not asset_ids:
            return PlaybackCycle(
                collection_key=playback_key, mode=mode, cycle_id="empty", order=[], position=0
            )

        eligible = list(dict.fromkeys(asset_ids))
        existing = self.playback_repo.get_cycle(playback_key)
        if existing is None or existing.mode != mode or not existing.order:
            return self._deal_cycle(playback_key, mode, eligible)

        eligible_set = set(eligible)
        position = min(existing.position, len(existing.order))
        shown = [asset_id for asset_id in existing.order[:position] if asset_id in eligible_set]
        remaining = [
            asset_id for asset_id in existing.order[position:] if asset_id in eligible_set
        ]
        known = set(existing.order)
        fresh = [asset_id for asset_id in eligible if asset_id not in known]

        if not remaining and not fresh:
            # The whole pass has been shown: deal the next one.
            return self._deal_cycle(playback_key, mode, eligible)

        if fresh:
            head = max(NEW_ASSET_HEAD_MIN_SLOTS, len(remaining) // NEW_ASSET_HEAD_FRACTION)
            for asset_id in fresh:
                remaining.insert(random.randint(0, min(head, len(remaining))), asset_id)

        order = shown + remaining
        if order == existing.order and position == existing.position:
            return existing
        return self.playback_repo.save_cycle(
            PlaybackCycle(
                collection_key=playback_key,
                mode=mode,
                cycle_id=existing.cycle_id,
                order=order,
                position=len(shown),
            )
        )

    def _deal_cycle(self, playback_key: str, mode: str, asset_ids: list[str]) -> PlaybackCycle:
        if mode == PLAYBACK_MODE_SHUFFLE_RANDOM:
            # Bag disabled by the administrator: sample with replacement so repeats within a pass
            # are expected, which is the behaviour the setting's off state promises.
            order = random.choices(asset_ids, k=len(asset_ids))
        else:
            order = random.sample(asset_ids, k=len(asset_ids))
        return self.playback_repo.save_cycle(
            PlaybackCycle(
                collection_key=playback_key,
                mode=mode,
                cycle_id=uuid4().hex,
                order=order,
                position=0,
            )
        )

    def refresh_playlist_cache(self) -> str:
        global _PLAYLIST_CACHE_INVALIDATED_AT
        invalidated_at = datetime.now(timezone.utc)
        with _PLAYLIST_CACHE_LOCK:
            _PLAYLIST_CACHE.clear()
            _PLAYLIST_CACHE_INVALIDATED_AT = invalidated_at
        LOGGER.info(
            "display_playlist_cache_refreshed",
            invalidated_at=invalidated_at.isoformat(),
        )
        return invalidated_at.isoformat()

    def _compute_playlist_revision(
        self,
        *,
        profile: DisplayProfile,
        collection_id: str | None,
        collection: object | None,
        sleep_schedule: SleepSchedule,
        cycle: PlaybackCycle | None = None,
    ) -> str:
        stats = self.asset_repo.get_playlist_asset_stats(collection_id=collection_id)
        revision_input = "|".join(
            [
                profile.id,
                profile.name,
                profile.selected_collection_id or "",
                profile.updated_at,
                str(profile.slideshow_interval_seconds),
                profile.transition_mode,
                str(profile.transition_duration_ms),
                profile.fit_mode,
                str(profile.shuffle_enabled),
                str(profile.shuffle_bag_enabled),
                profile.idle_message,
                str(profile.refresh_interval_seconds),
                profile.background_fill_mode,
                "" if collection is None else str(getattr(collection, "id", "")),
                "" if collection is None else str(getattr(collection, "name", "")),
                "" if collection is None else str(getattr(collection, "updated_at", "")),
                str(stats.asset_count),
                stats.latest_updated_at or "",
                # Pin the served item order to the cycle it was dealt for, so a rollover or a
                # reconcile cannot be answered from a stale cached ordering.
                "" if cycle is None else cycle.mode,
                "" if cycle is None else cycle.cycle_id,
                "" if cycle is None else hashlib.sha256(",".join(cycle.order).encode()).hexdigest(),
                json.dumps(asdict(sleep_schedule), sort_keys=True),
            ]
        )
        return (
            hashlib.sha256(revision_input.encode("utf-8")).hexdigest()[:16]
            if revision_input
            else "empty"
        )

    @staticmethod
    def _get_cached_playlist(
        cache_key: tuple[str, str]
    ) -> DisplayPlaylist | None:
        with _PLAYLIST_CACHE_LOCK:
            playlist = _PLAYLIST_CACHE.get(cache_key)
            if playlist is None:
                return None
            _PLAYLIST_CACHE.move_to_end(cache_key)
            return playlist

    @staticmethod
    def _store_cached_playlist(
        cache_key: tuple[str, str], playlist: DisplayPlaylist
    ) -> None:
        with _PLAYLIST_CACHE_LOCK:
            _PLAYLIST_CACHE[cache_key] = playlist
            _PLAYLIST_CACHE.move_to_end(cache_key)
            while len(_PLAYLIST_CACHE) > _PLAYLIST_CACHE_MAX_ENTRIES:
                _PLAYLIST_CACHE.popitem(last=False)

    def _background_from_metadata(self, metadata_json: str) -> AssetBackground | None:
        try:
            metadata = json.loads(metadata_json)
        except (json.JSONDecodeError, TypeError):
            return None
        
        # Check for stored background metadata first
        stored_background = metadata.get("background")
        if isinstance(stored_background, dict):
            return background_meta_from_dict(stored_background)
        
        # Fallback to palette-based background
        palette = metadata.get("palette")
        if not isinstance(palette, list) or not palette:
            return None
        return AssetBackground(
            dominant_color=str(palette[0]),
            palette=[str(c) for c in palette[:5]],
        )

    def count_new_assets_since(self, since_timestamp: str, collection_id: str | None = None) -> int:
        """Count assets imported since a given timestamp."""
        count = self.asset_repo.count_new_assets_since(since_timestamp, collection_id)
        if self._was_cache_refreshed_since(since_timestamp):
            return count + 1
        return count

    @staticmethod
    def _was_cache_refreshed_since(since_timestamp: str) -> bool:
        with _PLAYLIST_CACHE_LOCK:
            invalidated_at = _PLAYLIST_CACHE_INVALIDATED_AT

        if invalidated_at is None:
            return False

        parsed_since = DisplayService._parse_iso_timestamp(since_timestamp)
        if parsed_since is None:
            return False

        return invalidated_at > parsed_since

    @staticmethod
    def _parse_iso_timestamp(value: str) -> datetime | None:
        normalized = value.strip()
        if not normalized:
            return None
        if normalized.endswith("Z"):
            normalized = f"{normalized[:-1]}+00:00"

        try:
            parsed = datetime.fromisoformat(normalized)
        except ValueError:
            return None

        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)

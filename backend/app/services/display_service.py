from __future__ import annotations

from collections import OrderedDict
from dataclasses import asdict
import hashlib
import json
import threading
import structlog

from app.models.asset import AssetBackground
from app.models.display import DisplayPlaylist, DisplayProfile, PlaylistItem
from app.models.sleep_schedule import SleepSchedule
from app.repositories.asset_repository import AssetRepository
from app.repositories.collection_repository import CollectionRepository
from app.repositories.display_repository import DisplayRepository
from app.repositories.settings_repository import SettingsRepository
from app.services.background_service import (
    VALID_BACKGROUND_FILL_MODES,
    background_meta_from_dict,
)

LOGGER = structlog.get_logger(__name__)
_PLAYLIST_CACHE_MAX_ENTRIES = 4
_PLAYLIST_CACHE: OrderedDict[tuple[str, str], DisplayPlaylist] = OrderedDict()
_PLAYLIST_CACHE_LOCK = threading.Lock()


class DisplayService:
    def __init__(
        self,
        display_repo: DisplayRepository | None = None,
        asset_repo: AssetRepository | None = None,
        collection_repo: CollectionRepository | None = None,
        settings_repo: SettingsRepository | None = None,
    ) -> None:
        self.display_repo = display_repo or DisplayRepository()
        self.asset_repo = asset_repo or AssetRepository()
        self.collection_repo = collection_repo or CollectionRepository()
        self.settings_repo = settings_repo or SettingsRepository()

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
        playlist_revision = self._compute_playlist_revision(
            profile=profile,
            collection_id=resolved_collection_id,
            collection=collection,
            sleep_schedule=sleep_schedule,
        )
        cache_key = (resolved_collection_id or "", playlist_revision)
        cached = self._get_cached_playlist(cache_key)
        if cached is not None:
            return cached

        assets = self.asset_repo.list_playlist_assets(collection_id=resolved_collection_id)

        # Assets are already ordered by imported_at desc (newest first)
        # When shuffle is enabled, we still want new assets to appear sooner
        # Strategy: Put assets imported in the last 24 hours at the front, then shuffle the rest
        if profile.shuffle_enabled:
            from datetime import datetime, timezone, timedelta
            cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
            new_assets = [a for a in assets if a.imported_at > cutoff]
            older_assets = [a for a in assets if a.imported_at <= cutoff]
            
            # Shuffle older assets
            import random
            random.shuffle(older_assets)
            
            # New assets first (also shuffled among themselves), then older shuffled assets
            random.shuffle(new_assets)
            assets = new_assets + older_assets
        else:
            # Non-shuffle: newest first (already sorted by imported_at desc)
            pass

        items = []
        for asset in assets:
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
            background_fill_mode=profile.background_fill_mode,
            sleep_schedule=sleep_schedule,
            items=items,
        )
        self._store_cached_playlist(cache_key, playlist)
        return playlist

    def _compute_playlist_revision(
        self,
        *,
        profile: DisplayProfile,
        collection_id: str | None,
        collection: object | None,
        sleep_schedule: SleepSchedule,
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
        return self.asset_repo.count_new_assets_since(since_timestamp, collection_id)

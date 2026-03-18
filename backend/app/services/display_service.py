from __future__ import annotations

import hashlib
import json
import structlog
from pathlib import Path

from app.models.asset import AssetBackground
from app.models.display import DisplayPlaylist, DisplayProfile, PlaylistItem
from app.models.settings import FrameSettings
from app.repositories.asset_repository import AssetRepository
from app.repositories.collection_repository import CollectionRepository
from app.repositories.display_repository import DisplayRepository
from app.repositories.settings_repository import SettingsRepository
from app.services.background_service import (
    VALID_BACKGROUND_FILL_MODES,
    background_meta_from_dict,
    derive_background_meta,
)

LOGGER = structlog.get_logger(__name__)


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
        assets = self.asset_repo.list_assets(collection_id=resolved_collection_id)
        revision_input = "|".join(
            [profile.updated_at, *(asset.updated_at for asset in assets)]
        )
        playlist_revision = (
            hashlib.sha256(revision_input.encode("utf-8")).hexdigest()[:16]
            if revision_input
            else "empty"
        )

        if profile.shuffle_enabled:
            assets = sorted(
                assets,
                key=lambda asset: hashlib.sha256(
                    f"{profile.id}:{playlist_revision}:{asset.id}:{asset.checksum_sha256}".encode(
                        "utf-8"
                    )
                ).hexdigest(),
            )
        else:
            assets = sorted(
                assets,
                key=lambda asset: (asset.filename.lower(), asset.imported_at, asset.id),
            )

        items = []
        for asset in assets:
            background = self._resolve_background(asset)
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
        return DisplayPlaylist(
            profile=profile,
            collection_id=resolved_collection_id,
            collection_name=None if collection is None else collection.name,
            shuffle_enabled=profile.shuffle_enabled,
            playlist_revision=playlist_revision,
            background_fill_mode=profile.background_fill_mode,
            sleep_schedule=self.settings_repo.get_sleep_schedule(),
            items=items,
        )

    def _resolve_background(self, asset: object) -> AssetBackground | None:
        """Return the background metadata for *asset*, deriving and caching it lazily.

        Returns ``None`` on any failure so playlist assembly is never blocked.
        """
        try:
            meta: dict[str, object] = json.loads(
                getattr(asset, "metadata_json", "{}") or "{}"
            )
        except (json.JSONDecodeError, TypeError):
            meta = {}

        stored_background = meta.get("background")
        if isinstance(stored_background, dict):
            return background_meta_from_dict(stored_background)

        # Lazy derivation — find the display variant path and compute colours.
        try:
            display_variant = next(
                (
                    variant
                    for variant in getattr(asset, "variants", [])
                    if getattr(variant, "kind", "") == "display"
                ),
                None,
            )
            if display_variant is None:
                display_variant = self.asset_repo.get_variant(asset.id, "display")  # type: ignore[union-attr]
            if display_variant is None:
                return None
            variant_path = Path(display_variant.local_path)
            if not variant_path.is_file():
                return None

            bg = derive_background_meta(variant_path)

            # Persist so subsequent requests skip derivation.
            meta["background"] = {
                "dominant_color": bg.dominant_color,
                "gradient_colors": bg.gradient_colors,
            }
            self.asset_repo.update_metadata_json(
                asset.id, json.dumps(meta, sort_keys=True)
            )  # type: ignore[union-attr]

            return bg
        except Exception:
            LOGGER.warning(
                "background_derivation_failed",
                asset_id=getattr(asset, "id", None),
                exc_info=True,
            )
            return None

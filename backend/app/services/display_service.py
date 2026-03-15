from __future__ import annotations

import hashlib

from app.models.display import DisplayPlaylist, DisplayProfile, PlaylistItem
from app.models.settings import FrameSettings
from app.repositories.asset_repository import AssetRepository
from app.repositories.collection_repository import CollectionRepository
from app.repositories.display_repository import DisplayRepository
from app.repositories.settings_repository import SettingsRepository


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
        profile = self.display_repo.get_default_profile()
        if profile is None:
            settings = self.settings_repo.get_settings()
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
            )
        return profile

    def update_config(self, updates: dict[str, object]) -> DisplayProfile:
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
        return updated_profile

    def get_playlist(self, collection_id: str | None = None) -> DisplayPlaylist:
        profile = self.get_config()
        resolved_collection_id = collection_id or profile.selected_collection_id
        collection = self.collection_repo.get_collection(resolved_collection_id) if resolved_collection_id else None
        assets = self.asset_repo.list_assets(collection_id=resolved_collection_id)
        revision_input = "|".join([profile.updated_at, *(asset.updated_at for asset in assets)])
        playlist_revision = hashlib.sha256(revision_input.encode("utf-8")).hexdigest()[:16] if revision_input else "empty"

        if profile.shuffle_enabled:
            assets = sorted(
                assets,
                key=lambda asset: hashlib.sha256(
                    f"{profile.id}:{playlist_revision}:{asset.id}:{asset.checksum_sha256}".encode("utf-8")
                ).hexdigest(),
            )
        else:
            assets = sorted(assets, key=lambda asset: (asset.filename.lower(), asset.imported_at, asset.id))

        items = []
        for asset in assets:
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
                )
            )
        return DisplayPlaylist(
            profile=profile,
            collection_id=resolved_collection_id,
            collection_name=None if collection is None else collection.name,
            shuffle_enabled=profile.shuffle_enabled,
            playlist_revision=playlist_revision,
            sleep_schedule=self.settings_repo.get_sleep_schedule(),
            items=items,
        )

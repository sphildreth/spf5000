from __future__ import annotations

from app.models.settings import FrameSettings
from app.repositories.display_repository import DisplayRepository
from app.repositories.settings_repository import SettingsRepository


class SettingsService:
    def __init__(
        self,
        repo: SettingsRepository | None = None,
        display_repo: DisplayRepository | None = None,
    ) -> None:
        self.repo = repo or SettingsRepository()
        self.display_repo = display_repo or DisplayRepository()

    def get_settings(self) -> FrameSettings:
        return self.repo.get_settings()

    def update_settings(self, settings: FrameSettings) -> FrameSettings:
        updated = self.repo.update_settings(settings)
        profile = self.display_repo.get_default_profile()
        if profile is not None:
            profile.selected_collection_id = updated.selected_collection_id
            profile.slideshow_interval_seconds = updated.slideshow_interval_seconds
            profile.transition_mode = updated.transition_mode
            profile.transition_duration_ms = updated.transition_duration_ms
            profile.fit_mode = updated.fit_mode
            profile.shuffle_enabled = updated.shuffle_enabled
            self.display_repo.update_profile(profile)
        return updated

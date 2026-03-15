from app.models.settings import FrameSettings
from app.repositories.settings_repository import SettingsRepository


class SettingsService:
    def __init__(self, repo: SettingsRepository | None = None) -> None:
        self.repo = repo or SettingsRepository()

    def get_settings(self) -> FrameSettings:
        return self.repo.get_settings()

    def update_settings(self, settings: FrameSettings) -> FrameSettings:
        return self.repo.update_settings(settings)

from __future__ import annotations

from pathlib import Path

from app.models.source import Source
from app.providers.google_photos import GooglePhotosProvider
from app.providers.local_files import LocalFilesProvider
from app.repositories.source_repository import SourceRepository


class SourceService:
    def __init__(self, repo: SourceRepository | None = None) -> None:
        self.repo = repo or SourceRepository()
        self.providers = {
            "local_files": LocalFilesProvider(),
            "google_photos": GooglePhotosProvider(),
        }

    def list_sources(self) -> list[Source]:
        return self.repo.list_sources()

    def get_source(self, source_id: str) -> Source | None:
        return self.repo.get_source(source_id)

    def update_source(self, source_id: str, name: str | None, import_path: str | None, enabled: bool | None) -> Source | None:
        existing = self.repo.get_source(source_id)
        if existing is None:
            return None
        if name is not None:
            existing.name = name
        if import_path is not None:
            existing.import_path = str(Path(import_path))
        if enabled is not None:
            existing.enabled = enabled
        return self.repo.update_source(existing)

    def get_provider(self, provider_type: str) -> object:
        provider = self.providers.get(provider_type)
        if provider is None:
            raise ValueError(f"Unsupported provider type: {provider_type}")
        return provider

from __future__ import annotations

from app.providers.local_files import LocalFilesProvider


class SourceService:
    def __init__(self) -> None:
        self.providers = {"local_files": LocalFilesProvider()}

    def list_sources(self) -> list[dict[str, str]]:
        return [{"id": key, "name": provider.provider_name()} for key, provider in self.providers.items()]

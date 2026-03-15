from __future__ import annotations

from typing import Any


class LocalFilesProvider:
    def provider_name(self) -> str:
        return "local_files"

    def health_check(self) -> dict[str, Any]:
        return {"ok": True, "provider": self.provider_name()}

    def list_collections(self) -> list[dict[str, Any]]:
        return []

    def sync_collection(self, collection_id: str) -> dict[str, Any]:
        return {"ok": True, "collection_id": collection_id}

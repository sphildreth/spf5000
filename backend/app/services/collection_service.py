from __future__ import annotations

import re
from uuid import uuid4

from app.models.collection import Collection
from app.repositories.base import utc_now
from app.repositories.collection_repository import CollectionRepository


class CollectionService:
    def __init__(self, repo: CollectionRepository | None = None) -> None:
        self.repo = repo or CollectionRepository()

    def list_collections(self) -> list[Collection]:
        return self.repo.list_collections()

    def get_collection(self, collection_id: str) -> Collection | None:
        return self.repo.get_collection(collection_id)

    def create_collection(self, name: str, description: str, source_id: str | None, is_active: bool) -> Collection:
        now = utc_now()
        slug = re.sub(r"[^a-z0-9]+", "-", name.strip().lower()).strip("-") or "collection"
        collection = Collection(
            id=f"collection-{slug}-{uuid4().hex[:8]}",
            name=name,
            description=description,
            source_id=source_id,
            is_default=False,
            is_active=is_active,
            created_at=now,
            updated_at=now,
        )
        return self.repo.create_collection(collection)

    def update_collection(
        self,
        collection_id: str,
        name: str | None,
        description: str | None,
        source_id: str | None,
        is_active: bool | None,
    ) -> Collection | None:
        existing = self.repo.get_collection(collection_id)
        if existing is None:
            return None
        if name is not None:
            existing.name = name
        if description is not None:
            existing.description = description
        if source_id is not None:
            existing.source_id = source_id
        if is_active is not None:
            existing.is_active = is_active
        return self.repo.update_collection(existing)

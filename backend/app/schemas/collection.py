from __future__ import annotations

from dataclasses import asdict

from pydantic import BaseModel

from app.models.collection import Collection


class CollectionResponse(BaseModel):
    id: str
    name: str
    description: str
    source_id: str | None
    is_default: bool
    is_active: bool
    created_at: str
    updated_at: str
    asset_count: int

    @classmethod
    def from_domain(cls, collection: Collection) -> "CollectionResponse":
        return cls(**asdict(collection))


class CollectionCreateRequest(BaseModel):
    name: str
    description: str = ""
    source_id: str | None = None
    is_active: bool = True


class CollectionUpdateRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    source_id: str | None = None
    is_active: bool | None = None

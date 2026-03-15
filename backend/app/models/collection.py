from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class Collection:
    id: str
    name: str
    description: str
    source_id: str | None
    is_default: bool
    is_active: bool
    created_at: str
    updated_at: str
    asset_count: int = 0

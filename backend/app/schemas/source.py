from __future__ import annotations

from dataclasses import asdict

from pydantic import BaseModel

from app.models.source import Source


class SourceResponse(BaseModel):
    id: str
    name: str
    provider_type: str
    import_path: str
    enabled: bool
    created_at: str
    updated_at: str
    last_scan_at: str | None = None
    last_import_at: str | None = None
    asset_count: int

    @classmethod
    def from_domain(cls, source: Source) -> "SourceResponse":
        return cls(**asdict(source))


class SourceUpdateRequest(BaseModel):
    name: str | None = None
    import_path: str | None = None
    enabled: bool | None = None

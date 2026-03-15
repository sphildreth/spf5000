from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class Source:
    id: str
    name: str
    provider_type: str
    import_path: str
    enabled: bool
    created_at: str
    updated_at: str
    last_scan_at: str | None = None
    last_import_at: str | None = None
    asset_count: int = 0

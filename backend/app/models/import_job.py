from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class ImportJob:
    id: str
    job_type: str
    status: str
    source_id: str | None
    collection_id: str | None
    import_path: str
    discovered_count: int
    imported_count: int
    duplicate_count: int
    skipped_count: int
    error_count: int
    sample_filenames: list[str] = field(default_factory=list)
    message: str = ""
    started_at: str = ""
    completed_at: str | None = None

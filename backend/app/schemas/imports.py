from __future__ import annotations

from dataclasses import asdict

from pydantic import BaseModel, Field

from app.db.bootstrap import DEFAULT_COLLECTION_ID, DEFAULT_SOURCE_ID
from app.models.import_job import ImportJob


class LocalImportScanRequest(BaseModel):
    source_id: str = DEFAULT_SOURCE_ID
    max_samples: int = Field(default=10, ge=1, le=100)


class LocalImportRunRequest(BaseModel):
    source_id: str = DEFAULT_SOURCE_ID
    collection_id: str = DEFAULT_COLLECTION_ID
    max_samples: int = Field(default=10, ge=1, le=100)


class ImportJobResponse(BaseModel):
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
    sample_filenames: list[str]
    message: str
    started_at: str
    completed_at: str | None

    @classmethod
    def from_domain(cls, job: ImportJob) -> "ImportJobResponse":
        return cls(**asdict(job))


class LocalImportScanResponse(BaseModel):
    job: ImportJobResponse
    import_path: str
    discovered_count: int
    ignored_count: int
    sample_filenames: list[str]

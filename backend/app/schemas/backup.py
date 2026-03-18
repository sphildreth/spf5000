from __future__ import annotations

from pydantic import BaseModel

from app.services.backup_service import DatabaseRestoreResult


class DatabaseImportResponse(BaseModel):
    restored: bool
    reauthenticate_required: bool
    media_restored: bool
    message: str

    @classmethod
    def from_domain(cls, result: DatabaseRestoreResult) -> "DatabaseImportResponse":
        return cls(
            restored=result.restored,
            reauthenticate_required=result.reauthenticate_required,
            media_restored=result.media_restored,
            message=result.message,
        )

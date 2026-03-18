from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, File, HTTPException, Request, UploadFile, status
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask

from app.schemas.backup import DatabaseImportResponse
from app.services.backup_service import BackupService

router = APIRouter()
service = BackupService()


@router.get("/database/export")
def export_database() -> FileResponse:
    try:
        archive = service.export_database_archive()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return FileResponse(
        path=archive.path,
        media_type=archive.media_type,
        filename=archive.filename,
        background=BackgroundTask(service.cleanup_archive, archive.path),
    )


@router.post("/database/import", response_model=DatabaseImportResponse)
def import_database_backup(
    request: Request,
    archive: Annotated[UploadFile, File(description="Database backup ZIP archive")],
) -> DatabaseImportResponse:
    try:
        result = service.restore_database_archive(archive.file, request.app)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    finally:
        archive.file.close()

    request.session.clear()
    return DatabaseImportResponse.from_domain(result)


@router.get("/collections/{collection_id}/export")
def export_collection(collection_id: str) -> FileResponse:
    try:
        archive = service.export_collection_archive(collection_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return FileResponse(
        path=archive.path,
        media_type=archive.media_type,
        filename=archive.filename,
        background=BackgroundTask(service.cleanup_archive, archive.path),
    )

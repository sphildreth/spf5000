from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import require_admin
from app.schemas.logs import LogViewerResponse
from app.services.log_service import DEFAULT_LINE_LIMIT, MAX_LINE_LIMIT, LogService

router = APIRouter()
_log_service = LogService()


@router.get("/logs", response_model=LogViewerResponse)
def get_logs(
    file: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=MAX_LINE_LIMIT)] = DEFAULT_LINE_LIMIT,
    _admin: dict = Depends(require_admin),
) -> LogViewerResponse:
    try:
        return _log_service.get_logs(selected_file=file, line_limit=limit)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

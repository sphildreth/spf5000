from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Response

from app.api.deps import require_admin
from app.schemas.doctor import DoctorResponse
from app.services.doctor_service import DoctorService

router = APIRouter()
_log = logging.getLogger(__name__)

_doctor_service = DoctorService()


@router.get("/doctor", response_model=DoctorResponse)
def get_doctor_report(admin: dict = Depends(require_admin)) -> DoctorResponse:
    return _doctor_service.run_all_checks()


@router.post("/doctor/refresh", response_model=DoctorResponse)
def refresh_doctor_report(admin: dict = Depends(require_admin)) -> DoctorResponse:
    username = admin.get("username", "unknown")
    _log.info("doctor_refresh_triggered username=%s", username)
    return _doctor_service.run_all_checks()


@router.get("/doctor/export")
def export_doctor_report(admin: dict = Depends(require_admin)) -> Response:
    export_time = datetime.now(timezone.utc).isoformat()
    export_data = _doctor_service.build_support_snapshot()
    return Response(
        content=json.dumps(export_data, indent=2),
        media_type="application/json",
        headers={
            "Content-Disposition": (
                f"attachment; filename=spf5000-support-snapshot-{export_time[:10]}.json"
            )
        },
    )

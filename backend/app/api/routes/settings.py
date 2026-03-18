from fastapi import APIRouter, Depends

from app.models.settings import FrameSettings
from app.models.sleep_schedule import SleepSchedule
from app.schemas.settings import (
    SettingsResponse,
    SettingsUpdateRequest,
    SleepScheduleResponse,
    SleepScheduleTimeReferenceResponse,
    SleepScheduleUpdateRequest,
)
from app.services.settings_service import SettingsService

router = APIRouter()


def get_settings_service() -> SettingsService:
    return SettingsService()


@router.get("", response_model=SettingsResponse)
def get_settings(
    svc: SettingsService = Depends(get_settings_service),
) -> SettingsResponse:
    return SettingsResponse.from_domain(svc.get_settings())


@router.put("", response_model=SettingsResponse)
def update_settings(
    request: SettingsUpdateRequest,
    svc: SettingsService = Depends(get_settings_service),
) -> SettingsResponse:
    updated = svc.update_settings(FrameSettings(**request.model_dump()))
    return SettingsResponse.from_domain(updated)


@router.get("/sleep-schedule", response_model=SleepScheduleResponse)
def get_sleep_schedule(
    svc: SettingsService = Depends(get_settings_service),
) -> SleepScheduleResponse:
    return SleepScheduleResponse.from_domain(svc.get_sleep_schedule())


@router.put("/sleep-schedule", response_model=SleepScheduleResponse)
def update_sleep_schedule(
    request: SleepScheduleUpdateRequest,
    svc: SettingsService = Depends(get_settings_service),
) -> SleepScheduleResponse:
    schedule = SleepSchedule(
        sleep_schedule_enabled=request.sleep_schedule_enabled,
        sleep_start_local_time=request.sleep_start_local_time,
        sleep_end_local_time=request.sleep_end_local_time,
        display_timezone=request.display_timezone,
    )
    updated = svc.update_sleep_schedule(schedule)
    return SleepScheduleResponse.from_domain(updated)


@router.get("/time-reference", response_model=SleepScheduleTimeReferenceResponse)
def get_sleep_schedule_time_reference(
    svc: SettingsService = Depends(get_settings_service),
) -> SleepScheduleTimeReferenceResponse:
    return SleepScheduleTimeReferenceResponse.from_domain(
        svc.get_sleep_schedule_time_reference()
    )

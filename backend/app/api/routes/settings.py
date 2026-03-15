from fastapi import APIRouter

from app.models.settings import FrameSettings
from app.models.sleep_schedule import SleepSchedule
from app.schemas.settings import SettingsResponse, SettingsUpdateRequest, SleepScheduleResponse, SleepScheduleUpdateRequest
from app.services.settings_service import SettingsService

router = APIRouter()
service = SettingsService()


@router.get("", response_model=SettingsResponse)
def get_settings() -> SettingsResponse:
    current_settings = service.get_settings()
    return SettingsResponse.from_domain(current_settings)


@router.put("", response_model=SettingsResponse)
def update_settings(request: SettingsUpdateRequest) -> SettingsResponse:
    updated = service.update_settings(FrameSettings(**request.model_dump()))
    return SettingsResponse.from_domain(updated)


@router.get("/sleep-schedule", response_model=SleepScheduleResponse)
def get_sleep_schedule() -> SleepScheduleResponse:
    schedule = service.get_sleep_schedule()
    return SleepScheduleResponse.from_domain(schedule)


@router.put("/sleep-schedule", response_model=SleepScheduleResponse)
def update_sleep_schedule(request: SleepScheduleUpdateRequest) -> SleepScheduleResponse:
    schedule = SleepSchedule(
        sleep_schedule_enabled=request.sleep_schedule_enabled,
        sleep_start_local_time=request.sleep_start_local_time,
        sleep_end_local_time=request.sleep_end_local_time,
    )
    updated = service.update_sleep_schedule(schedule)
    return SleepScheduleResponse.from_domain(updated)

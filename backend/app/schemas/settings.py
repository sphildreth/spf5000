from pydantic import BaseModel


class SettingsResponse(BaseModel):
    slideshow_interval_seconds: int
    transition_mode: str
    fit_mode: str
    shuffle_enabled: bool


class SettingsUpdateRequest(BaseModel):
    slideshow_interval_seconds: int
    transition_mode: str
    fit_mode: str
    shuffle_enabled: bool

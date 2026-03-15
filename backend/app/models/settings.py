from dataclasses import dataclass


@dataclass(slots=True)
class FrameSettings:
    slideshow_interval_seconds: int = 30
    transition_mode: str = "fade"
    fit_mode: str = "contain"
    shuffle_enabled: bool = True

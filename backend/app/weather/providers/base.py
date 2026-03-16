from __future__ import annotations

from typing import Any, Protocol

from app.models.weather import WeatherAlert, WeatherCurrentConditions, WeatherLocation


class WeatherProvider(Protocol):
    def provider_name(self) -> str: ...

    def provider_display_name(self) -> str: ...

    def health_check(self, location: WeatherLocation | None) -> dict[str, Any]: ...

    def get_current_conditions(self, location: WeatherLocation) -> WeatherCurrentConditions: ...

    def get_active_alerts(self, location: WeatherLocation) -> list[WeatherAlert]: ...

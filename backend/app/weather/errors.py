from __future__ import annotations


class WeatherError(RuntimeError):
    pass


class WeatherConfigurationError(WeatherError):
    pass


class WeatherProviderError(WeatherError):
    pass

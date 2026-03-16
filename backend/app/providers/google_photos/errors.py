from __future__ import annotations


class GooglePhotosError(Exception):
    """Base exception for Google Photos provider failures."""


class GooglePhotosConfigurationError(GooglePhotosError):
    """Raised when runtime configuration is missing or invalid."""


class GooglePhotosApiError(GooglePhotosError):
    def __init__(self, message: str, *, status_code: int | None = None, payload: object | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.payload = payload


class GooglePhotosAuthorizationPending(GooglePhotosError):
    """Raised while the OAuth device code flow is still awaiting user action."""


class GooglePhotosAuthorizationDenied(GooglePhotosError):
    """Raised when the user denies the OAuth device code flow."""


class GooglePhotosAuthorizationExpired(GooglePhotosError):
    """Raised when the device code flow expires."""


class GooglePhotosSlowDown(GooglePhotosError):
    def __init__(self, interval_seconds: int) -> None:
        super().__init__("Google requested a slower polling cadence")
        self.interval_seconds = interval_seconds

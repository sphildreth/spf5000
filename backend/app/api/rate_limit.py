from __future__ import annotations

import os
import threading
import time
from collections import defaultdict

from fastapi import Depends, HTTPException, Request

_request_counts: dict[str, list[float]] = defaultdict(list)
_request_lock = threading.Lock()
_last_global_prune_at = 0.0
_largest_tracked_window_seconds = 0.0
_GLOBAL_PRUNE_INTERVAL_SECONDS = 60.0
_MAX_TRACKED_IPS = 1024


_TRUTHY = {"true", "1", "yes", "on"}
_FALSY = {"false", "0", "no", "off"}


def _env_override(name: str) -> bool | None:
    """Return a boolean when an environment variable explicitly overrides a config key."""
    value = os.environ.get(name)
    if value is None:
        return None
    normalized = value.strip().lower()
    if normalized in _TRUTHY:
        return True
    if normalized in _FALSY:
        return False
    return None


def is_rate_limit_enabled() -> bool:
    """Whether rate limiting is active, resolved per call.

    ``SPF5000_RATE_LIMIT`` overrides the ``[security] rate_limit_enabled`` config key so
    tests and development can toggle limiting without editing the config file. Before this
    the config key existed but nothing read it, so disabling it had no effect.
    """
    override = _env_override("SPF5000_RATE_LIMIT")
    if override is not None:
        return override
    from app.core.config import settings

    return bool(settings.rate_limit_enabled)


def trust_proxy_enabled() -> bool:
    """Whether ``X-Forwarded-For`` may be trusted to identify callers."""
    override = _env_override("SPF5000_TRUST_PROXY")
    if override is not None:
        return override
    from app.core.config import settings

    return bool(settings.trust_proxy)


def client_ip(request: Request) -> str:
    """Resolve the caller identity used as a rate-limit bucket.

    ``X-Forwarded-For`` is only honoured when the deployment declares a trusted proxy
    (``[security] trust_proxy``), because SPF5000 normally terminates HTTP itself: trusting
    the header by default would let any LAN client rename its way past a limit.
    """
    if trust_proxy_enabled():
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def enforce_rate_limit(request: Request, limit: str) -> None:
    """Raise HTTP 429 when ``limit`` (for example ``"120/minute"``) is exceeded."""
    if not check_rate_limit(client_ip(request), limit):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")


def rate_limited(limit: str):
    """Build a route dependency that applies ``limit`` to every request.

    Limits are sized well above legitimate appliance traffic (a kiosk refreshes the
    playlist at most every 15s and reports playback once per slide, with the fastest
    permitted slide interval of 1s) so the limit is a backstop against runaway clients
    rather than a source of visible glitches.
    """

    def dependency(request: Request) -> None:
        enforce_rate_limit(request, limit)

    return Depends(dependency)


def check_rate_limit(ip_address: str, limit: str) -> bool:
    """Check if the request from ip_address exceeds the rate limit.

    Each caller has an independent budget per limit string. Returns True if the request is
    allowed, False if rate limited.
    """
    if not is_rate_limit_enabled():
        return True

    parts = limit.split("/")
    if len(parts) != 2:
        return True

    count_str, period_str = parts
    try:
        limit_count = int(count_str)
    except ValueError:
        return True

    period_seconds: float
    if period_str == "second":
        period_seconds = 1
    elif period_str == "minute":
        period_seconds = 60
    elif period_str == "hour":
        period_seconds = 3600
    elif period_str == "day":
        period_seconds = 86400
    else:
        return True

    now = time.time()
    cutoff = now - period_seconds

    with _request_lock:
        global _last_global_prune_at, _largest_tracked_window_seconds

        if period_seconds > _largest_tracked_window_seconds:
            _largest_tracked_window_seconds = period_seconds

        if (
            _largest_tracked_window_seconds > 0
            and now - _last_global_prune_at >= _GLOBAL_PRUNE_INTERVAL_SECONDS
        ) or len(_request_counts) > _MAX_TRACKED_IPS:
            stale_cutoff = now - _largest_tracked_window_seconds
            for tracked_ip, tracked_requests in list(_request_counts.items()):
                tracked_requests[:] = [t for t in tracked_requests if t > stale_cutoff]
                if not tracked_requests:
                    del _request_counts[tracked_ip]
            _last_global_prune_at = now

        # Bucket per caller *and* limit: keying by caller alone would let one endpoint's
        # budget consume another's (six setup attempts plus five login attempts would have
        # blocked login even though neither endpoint exceeded its own limit).
        bucket = _bucket_key(ip_address, limit)
        requests = _request_counts[bucket]
        requests[:] = [t for t in requests if t > cutoff]

        if len(requests) >= limit_count:
            return False

        requests.append(now)
        return True


def _bucket_key(ip_address: str, limit: str) -> str:
    return f"{ip_address}|{limit}"

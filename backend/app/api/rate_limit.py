from __future__ import annotations

import os
import threading
import time
from collections import defaultdict

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

_request_counts: dict[str, list[float]] = defaultdict(list)
_request_lock = threading.Lock()
_last_global_prune_at = 0.0
_largest_tracked_window_seconds = 0.0
_GLOBAL_PRUNE_INTERVAL_SECONDS = 60.0


def is_rate_limit_enabled() -> bool:
    """Check if rate limiting is enabled. Reads env var at call time."""
    return os.environ.get("SPF5000_RATE_LIMIT", "true").lower() != "false"


def check_rate_limit(ip_address: str, limit: str) -> bool:
    """Check if the request from ip_address exceeds the rate limit.

    Returns True if the request is allowed, False if rate limited.
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
        ):
            stale_cutoff = now - _largest_tracked_window_seconds
            for tracked_ip, tracked_requests in list(_request_counts.items()):
                tracked_requests[:] = [t for t in tracked_requests if t > stale_cutoff]
                if not tracked_requests:
                    del _request_counts[tracked_ip]
            _last_global_prune_at = now

        requests = _request_counts[ip_address]
        requests[:] = [t for t in requests if t > cutoff]
        if not requests and ip_address in _request_counts:
            del _request_counts[ip_address]
            requests = _request_counts[ip_address]

        if len(requests) >= limit_count:
            return False

        requests.append(now)
        return True

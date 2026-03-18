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
        requests = _request_counts[ip_address]
        requests[:] = [t for t in requests if t > cutoff]

        if len(requests) >= limit_count:
            return False

        requests.append(now)
        return True

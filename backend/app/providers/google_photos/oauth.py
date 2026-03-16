from __future__ import annotations

import json
import math
from datetime import UTC, datetime, timedelta


def build_device_flow_state(*, request_id: str, display_name: str) -> str:
    return json.dumps({"requestId": request_id, "displayName": display_name}, sort_keys=True)


def utc_plus_seconds(seconds: int) -> str:
    return (datetime.now(UTC) + timedelta(seconds=max(0, seconds))).isoformat()


def parse_duration_seconds(value: str | None, default: int = 30) -> int:
    if not value:
        return default
    trimmed = value.strip()
    if trimmed.endswith("s"):
        trimmed = trimmed[:-1]
    try:
        return max(1, int(math.ceil(float(trimmed))))
    except ValueError:
        return default

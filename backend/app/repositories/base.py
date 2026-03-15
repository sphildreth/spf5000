from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def bool_to_int(value: bool) -> int:
    return 1 if value else 0


def int_to_bool(value: Any) -> bool:
    return bool(int(value or 0))


def row_to_dict(cursor: Any, row: Any) -> dict[str, Any] | None:
    if row is None:
        return None
    columns = [column[0] for column in getattr(cursor, "description", [])]
    return dict(zip(columns, row, strict=False))


def rows_to_dicts(cursor: Any, rows: list[Any]) -> list[dict[str, Any]]:
    columns = [column[0] for column in getattr(cursor, "description", [])]
    return [dict(zip(columns, row, strict=False)) for row in rows]


def json_dumps(value: Any) -> str:
    return json.dumps(value, sort_keys=True)


def json_loads(value: str | None, default: Any) -> Any:
    if not value:
        return default
    return json.loads(value)

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class AdminUser:
    id: str
    username: str
    password_hash: str
    enabled: bool
    created_at: str
    updated_at: str
    last_login_at: str | None = None

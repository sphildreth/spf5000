from __future__ import annotations

import uuid

from app.db.connection import get_connection, is_null_connection
from app.models.auth import AdminUser
from app.repositories.base import bool_to_int, int_to_bool, row_to_dict, utc_now


class AdminRepository:
    def auth_available(self) -> bool:
        with get_connection() as conn:
            return not is_null_connection(conn)

    # ------------------------------------------------------------------ admin users

    def create_admin(self, username: str, password_hash: str) -> AdminUser:
        now = utc_now()
        admin_id = str(uuid.uuid4())
        with get_connection() as conn:
            if is_null_connection(conn):
                return AdminUser(
                    id=admin_id,
                    username=username,
                    password_hash=password_hash,
                    enabled=True,
                    created_at=now,
                    updated_at=now,
                    last_login_at=now,
                )
            conn.execute(
                """
                insert into admin_users (
                    id,
                    username,
                    password_hash,
                    enabled,
                    created_at,
                    updated_at,
                    last_login_at
                )
                values (?, ?, ?, ?, ?, ?, ?)
                """,
                (admin_id, username, password_hash, bool_to_int(True), now, now, now),
            )
        return AdminUser(
            id=admin_id,
            username=username,
            password_hash=password_hash,
            enabled=True,
            created_at=now,
            updated_at=now,
            last_login_at=now,
        )

    def get_by_username(self, username: str) -> AdminUser | None:
        with get_connection() as conn:
            if is_null_connection(conn):
                return None
            cursor = conn.execute(
                "select * from admin_users where username = ?",
                (username,),
            )
            row = row_to_dict(cursor, cursor.fetchone())
        if row is None:
            return None
        return self._to_model(row)

    def get_by_id(self, admin_id: str) -> AdminUser | None:
        with get_connection() as conn:
            if is_null_connection(conn):
                return None
            cursor = conn.execute(
                "select * from admin_users where id = ?",
                (admin_id,),
            )
            row = row_to_dict(cursor, cursor.fetchone())
        if row is None:
            return None
        return self._to_model(row)

    def count_enabled_admins(self) -> int:
        with get_connection() as conn:
            if is_null_connection(conn):
                return 0
            cursor = conn.execute(
                "select count(*) from admin_users where enabled = 1",
            )
            row = cursor.fetchone()
        return int(row[0]) if row else 0

    # ------------------------------------------------------------------ system state

    def get_state(self, key: str) -> str | None:
        with get_connection() as conn:
            if is_null_connection(conn):
                return None
            cursor = conn.execute(
                "select value from system_state where key = ?",
                (key,),
            )
            row = cursor.fetchone()
        return str(row[0]) if row else None

    def set_state(self, key: str, value: str) -> None:
        now = utc_now()
        with get_connection() as conn:
            if is_null_connection(conn):
                return
            conn.execute(
                """
                insert into system_state (key, value, updated_at)
                values (?, ?, ?)
                on conflict(key) do update set value = excluded.value, updated_at = excluded.updated_at
                """,
                (key, value, now),
            )

    def record_login(self, admin_id: str) -> None:
        now = utc_now()
        with get_connection() as conn:
            if is_null_connection(conn):
                return
            conn.execute(
                """
                update admin_users
                set last_login_at = ?, updated_at = ?
                where id = ?
                """,
                (now, now, admin_id),
            )

    def is_bootstrapped(self) -> bool:
        return self.count_enabled_admins() > 0

    # ------------------------------------------------------------------ helpers

    def _to_model(self, row: dict) -> AdminUser:
        return AdminUser(
            id=str(row["id"]),
            username=str(row["username"]),
            password_hash=str(row["password_hash"]),
            enabled=int_to_bool(row["enabled"]),
            created_at=str(row["created_at"]),
            updated_at=str(row["updated_at"]),
            last_login_at=str(row["last_login_at"]) if row.get("last_login_at") else None,
        )

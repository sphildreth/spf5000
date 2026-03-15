from __future__ import annotations

import hashlib
import hmac
import os

from app.models.auth import AdminUser
from app.repositories.admin_repository import AdminRepository

PBKDF2_ITERATIONS = 600_000
_HASH_PREFIX = "pbkdf2:sha256"


def hash_password(password: str) -> str:
    """Hash *password* with PBKDF2-HMAC-SHA256 and a random 32-byte salt.

    Stored format:  pbkdf2:sha256:<iterations>:<salt_hex>:<key_hex>
    """
    salt = os.urandom(32)
    key = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, PBKDF2_ITERATIONS)
    return f"{_HASH_PREFIX}:{PBKDF2_ITERATIONS}:{salt.hex()}:{key.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    """Return True if *password* matches *stored_hash* using a timing-safe comparison."""
    try:
        prefix, algo, iterations_str, salt_hex, key_hex = stored_hash.split(":", 4)
    except ValueError:
        return False
    if f"{prefix}:{algo}" != _HASH_PREFIX:
        return False
    try:
        iterations = int(iterations_str)
        salt = bytes.fromhex(salt_hex)
        expected_key = bytes.fromhex(key_hex)
    except (ValueError, OverflowError):
        return False
    computed = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, iterations)
    return hmac.compare_digest(computed, expected_key)


class AuthService:
    def __init__(self, admin_repo: AdminRepository | None = None) -> None:
        self.admin_repo = admin_repo or AdminRepository()

    def auth_available(self) -> bool:
        return self.admin_repo.auth_available()

    def is_bootstrapped(self) -> bool:
        return self.admin_repo.is_bootstrapped()

    def setup(self, username: str, password: str) -> AdminUser:
        """Create the first admin account and mark the system as bootstrapped."""
        password_hash = hash_password(password)
        user = self.admin_repo.create_admin(username, password_hash)
        self.admin_repo.set_state("bootstrapped", "true")
        return user

    def authenticate(self, username: str, password: str) -> AdminUser | None:
        """Return the admin user if credentials are valid, otherwise None."""
        user = self.admin_repo.get_by_username(username)
        if user is None or not user.enabled:
            return None
        if not verify_password(password, user.password_hash):
            return None
        self.admin_repo.record_login(user.id)
        return user

    def get_active_user(self, admin_id: str) -> AdminUser | None:
        """Return the admin user for *admin_id* if they are enabled."""
        user = self.admin_repo.get_by_id(admin_id)
        if user is None or not user.enabled:
            return None
        return user

from __future__ import annotations

from pydantic import BaseModel, field_validator, model_validator


class SessionUserResponse(BaseModel):
    username: str


class SetupRequest(BaseModel):
    username: str
    password: str
    confirm_password: str

    @field_validator("username")
    @classmethod
    def username_not_empty(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("username must not be empty")
        return value

    @field_validator("password", "confirm_password")
    @classmethod
    def password_min_length(cls, value: str) -> str:
        if len(value) < 8:
            raise ValueError("password must be at least 8 characters")
        return value

    @model_validator(mode="after")
    def passwords_match(self) -> "SetupRequest":
        if self.password != self.confirm_password:
            raise ValueError("passwords do not match")
        return self


class LoginRequest(BaseModel):
    username: str
    password: str

    @field_validator("username")
    @classmethod
    def login_username_not_empty(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("username must not be empty")
        return value


class SessionResponse(BaseModel):
    auth_available: bool
    bootstrapped: bool
    authenticated: bool
    user: SessionUserResponse | None = None

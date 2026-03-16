from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator

from app.models.theme import ThemeDefinition, ThemeTokens


# ── Token-level validation schemas ────────────────────────────────────────────


class ThemeTokensSchema(BaseModel):
    """Pydantic validation schema for the tokens block inside a theme file."""

    colors: dict[str, str | int | float] = Field(min_length=1)
    typography: dict[str, str | int | float] = Field(min_length=1)
    spacing: dict[str, str | int | float] = Field(default_factory=dict)
    motion: dict[str, str | int | float] = Field(default_factory=dict)
    shape: dict[str, str | int | float] = Field(default_factory=dict)

    @field_validator("colors")
    @classmethod
    def _require_color_keys(cls, v: dict[str, str | int | float]) -> dict[str, str | int | float]:
        required = {"background_primary", "text_primary", "accent_primary"}
        missing = required - v.keys()
        if missing:
            raise ValueError(
                f"tokens.colors is missing required key(s): {sorted(missing)}"
            )
        return v

    @field_validator("typography")
    @classmethod
    def _require_typography_keys(
        cls, v: dict[str, str | int | float]
    ) -> dict[str, str | int | float]:
        required = {"font_family_base", "font_weight_normal"}
        missing = required - v.keys()
        if missing:
            raise ValueError(
                f"tokens.typography is missing required key(s): {sorted(missing)}"
            )
        if "font_size_md" not in v and "font_size_body" not in v:
            raise ValueError(
                "tokens.typography must include at least one of ['font_size_md', 'font_size_body']"
            )
        return v


def _stringify_tokens(values: dict[str, str | int | float]) -> dict[str, str]:
    return {key: str(value) for key, value in values.items()}


# ── Top-level theme file validation schema ────────────────────────────────────


class ThemeFileSchema(BaseModel):
    """Pydantic validation schema for a complete theme definition JSON file."""

    id: str = Field(min_length=1, max_length=80, pattern=r"^[a-z0-9][a-z0-9\-]*[a-z0-9]$")
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(min_length=1, max_length=500)
    version: str = Field(min_length=1, max_length=40)
    mode: str = Field(min_length=1, max_length=20, pattern=r"^(light|dark)$")
    tokens: ThemeTokensSchema
    components: dict[str, Any] = Field(default_factory=dict)
    contexts: dict[str, Any] = Field(default_factory=dict)

    def to_domain(self) -> ThemeDefinition:
        return ThemeDefinition(
            id=self.id,
            name=self.name,
            description=self.description,
            version=self.version,
            mode=self.mode,
            tokens=ThemeTokens(
                colors=_stringify_tokens(self.tokens.colors),
                typography=_stringify_tokens(self.tokens.typography),
                spacing=_stringify_tokens(self.tokens.spacing),
                motion=_stringify_tokens(self.tokens.motion),
                shape=_stringify_tokens(self.tokens.shape),
            ),
            components=dict(self.components),
            contexts=dict(self.contexts),
        )


# ── API response schemas ───────────────────────────────────────────────────────


class ThemeTokensResponse(BaseModel):
    colors: dict[str, str]
    typography: dict[str, str]
    spacing: dict[str, str]
    motion: dict[str, str]
    shape: dict[str, str]

    @classmethod
    def from_domain(cls, t: ThemeTokens) -> "ThemeTokensResponse":
        return cls(
            colors=t.colors,
            typography=t.typography,
            spacing=t.spacing,
            motion=t.motion,
            shape=t.shape,
        )


class ThemeDefinitionResponse(BaseModel):
    id: str
    name: str
    description: str
    version: str
    mode: str
    tokens: ThemeTokensResponse
    components: dict[str, Any]
    contexts: dict[str, Any]

    @classmethod
    def from_domain(cls, d: ThemeDefinition) -> "ThemeDefinitionResponse":
        return cls(
            id=d.id,
            name=d.name,
            description=d.description,
            version=d.version,
            mode=d.mode,
            tokens=ThemeTokensResponse.from_domain(d.tokens),
            components=d.components,
            contexts=d.contexts,
        )


class ThemesResponse(BaseModel):
    active_theme_id: str
    home_city_accent_style: str
    themes: list[ThemeDefinitionResponse]

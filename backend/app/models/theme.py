from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class ThemeTokens:
    """Resolved and validated token categories for a single theme."""

    colors: dict[str, str] = field(default_factory=dict)
    typography: dict[str, str] = field(default_factory=dict)
    spacing: dict[str, str] = field(default_factory=dict)
    motion: dict[str, str] = field(default_factory=dict)
    shape: dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class ThemeDefinition:
    """A fully-validated built-in theme definition loaded from a JSON file."""

    id: str
    name: str
    description: str
    version: str
    tokens: ThemeTokens
    components: dict = field(default_factory=dict)
    contexts: dict = field(default_factory=dict)

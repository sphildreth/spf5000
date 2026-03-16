from __future__ import annotations

import json
import logging
from pathlib import Path

from pydantic import ValidationError

from app.core.version import REPO_ROOT
from app.models.theme import ThemeDefinition
from app.schemas.theme import ThemeDefinitionResponse, ThemeFileSchema, ThemesResponse

_log = logging.getLogger(__name__)

_THEMES_DIR = REPO_ROOT / "themes"

# Stable canonical order for built-in themes.
_BUILTIN_ORDER = [
    "default-dark",
    "retro-neon",
    "purple-dream",
    "warm-family",
]


def _load_theme_file(path: Path) -> ThemeDefinition:
    """Load and validate a single theme JSON file.

    Raises ``ValueError`` with a descriptive message if the file is missing,
    malformed JSON, or fails schema validation.  Callers are responsible for
    deciding whether to propagate or skip the error.
    """
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ValueError(f"Could not read theme file {path}: {exc}") from exc

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in theme file {path}: {exc}") from exc

    try:
        parsed = ThemeFileSchema.model_validate(data)
    except ValidationError as exc:
        raise ValueError(
            f"Theme file {path.name!r} failed schema validation:\n{exc}"
        ) from exc

    return parsed.to_domain()


def _load_all_themes(themes_dir: Path) -> list[ThemeDefinition]:
    """Load all theme JSON files from *themes_dir*.

    Themes listed in ``_BUILTIN_ORDER`` are placed first (in that order).
    Any additional discovered JSON files are appended alphabetically.
    Files that fail validation are skipped with a logged error so one bad theme
    does not prevent the rest from loading.
    """
    if not themes_dir.is_dir():
        _log.warning("Themes directory not found: %s — no themes loaded", themes_dir)
        return []

    all_paths = sorted(themes_dir.glob("*.json"))
    path_by_stem = {p.stem: p for p in all_paths}

    ordered_stems = list(_BUILTIN_ORDER)
    for stem in sorted(path_by_stem.keys()):
        if stem not in ordered_stems:
            ordered_stems.append(stem)

    themes: list[ThemeDefinition] = []
    for stem in ordered_stems:
        path = path_by_stem.get(stem)
        if path is None:
            _log.debug("Expected built-in theme file not found: %s.json", stem)
            continue
        try:
            theme = _load_theme_file(path)
        except ValueError as exc:
            _log.error("Skipping theme file %s: %s", path.name, exc)
            continue
        if theme.id != stem:
            _log.error(
                "Theme file %s has id=%r which does not match filename stem %r; skipping",
                path.name,
                theme.id,
                stem,
            )
            continue
        themes.append(theme)

    return themes


class ThemeService:
    """Loads, validates, and serves built-in theme definitions.

    Themes are loaded once at first access and cached for the lifetime of the
    service instance.  The active ``theme_id`` and ``home_city_accent_style``
    are resolved from the settings repository at request time so they always
    reflect the current persisted values.
    """

    def __init__(self, themes_dir: Path | None = None) -> None:
        self._themes_dir = themes_dir or _THEMES_DIR
        self._cache: list[ThemeDefinition] | None = None

    # ── Internal helpers ───────────────────────────────────────────────────────

    def _get_themes(self) -> list[ThemeDefinition]:
        if self._cache is None:
            self._cache = _load_all_themes(self._themes_dir)
        return self._cache

    # ── Public API ─────────────────────────────────────────────────────────────

    def get_themes_response(
        self,
        active_theme_id: str,
        home_city_accent_style: str,
    ) -> ThemesResponse:
        """Return the full ``ThemesResponse`` for the public themes endpoint."""
        themes = self._get_themes()
        theme_ids = {t.id for t in themes}

        # Fall back to the first available theme if the active id is not found.
        resolved_theme_id = active_theme_id
        if active_theme_id not in theme_ids and themes:
            resolved_theme_id = themes[0].id
            _log.warning(
                "Active theme_id=%r not found in loaded themes; falling back to %r",
                active_theme_id,
                resolved_theme_id,
            )

        return ThemesResponse(
            active_theme_id=resolved_theme_id,
            home_city_accent_style=home_city_accent_style,
            themes=[ThemeDefinitionResponse.from_domain(t) for t in themes],
        )

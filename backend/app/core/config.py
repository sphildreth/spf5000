from __future__ import annotations

import logging
import os
import tomllib
from pathlib import Path
from typing import Any

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_DIR = Path(__file__).resolve().parents[2]
REPO_ROOT = BACKEND_DIR.parent

_log = logging.getLogger(__name__)


def _resolve_config_path() -> Path:
    config_path_env = os.environ.get("SPF5000_CONFIG")
    if config_path_env:
        return Path(config_path_env).expanduser()
    return REPO_ROOT / "spf5000.toml"


_CONFIG_PATH = _resolve_config_path()
_CONFIG_BASE_DIR = _CONFIG_PATH.parent


def _load_toml() -> dict[str, Any]:
    """Load runtime config from spf5000.toml, falling back to defaults if missing."""
    if not _CONFIG_PATH.exists():
        return {}
    try:
        with _CONFIG_PATH.open("rb") as fh:
            return tomllib.load(fh)
    except tomllib.TOMLDecodeError as exc:  # pragma: no cover
        _log.warning("Failed to parse %s: %s; using defaults", _CONFIG_PATH, exc)
        return {}


def _resolve_path(value: str | None, default: Path) -> Path:
    if not value:
        return default
    path = Path(value).expanduser()
    if path.is_absolute():
        return path
    return (_CONFIG_BASE_DIR / path).resolve()


_toml = _load_toml()
_server = _toml.get("server", {})
_paths = _toml.get("paths", {})
_logging = _toml.get("logging", {})
_security = _toml.get("security", {})
_data_dir_default = _resolve_path(_paths.get("data_dir"), BACKEND_DIR / "data")
_cache_dir_default = _resolve_path(_paths.get("cache_dir"), BACKEND_DIR / "cache")
_log_dir_default = _resolve_path(_paths.get("log_dir"), BACKEND_DIR / "logs")
_database_path_default = _resolve_path(_paths.get("database_path"), _data_dir_default / "spf5000.ddb")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    app_name: str = "SPF5000"
    app_version: str = "1.0.0"

    host: str = _server.get("host", "0.0.0.0")
    port: int = _server.get("port", 8000)
    debug: bool = _server.get("debug", False)
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173", "http://127.0.0.1:5173"])

    log_level: str = str(_logging.get("level", "INFO"))
    session_secret: str | None = _security.get("session_secret", None)

    data_dir: Path = _data_dir_default
    cache_dir: Path = _cache_dir_default
    log_dir: Path = _log_dir_default
    database_path: Path = _database_path_default
    frontend_dist_dir: Path = REPO_ROOT / "frontend" / "dist"
    legacy_frontend_dist_dir: Path = REPO_ROOT / "frontend_dist"

    display_max_width: int = 1920
    display_max_height: int = 1080
    thumbnail_max_size: int = 400
    jpeg_quality: int = 90
    playlist_sample_size: int = 20
    supported_image_extensions: tuple[str, ...] = (
        ".jpg",
        ".jpeg",
        ".png",
        ".webp",
        ".bmp",
        ".gif",
        ".tif",
        ".tiff",
    )

    @property
    def storage_dir(self) -> Path:
        return self.data_dir / "storage"

    @property
    def originals_dir(self) -> Path:
        return self.storage_dir / "originals"

    @property
    def variants_dir(self) -> Path:
        return self.storage_dir / "variants"

    @property
    def display_variants_dir(self) -> Path:
        return self.variants_dir / "display"

    @property
    def thumbnails_dir(self) -> Path:
        return self.variants_dir / "thumbnails"

    @property
    def staging_dir(self) -> Path:
        return self.data_dir / "staging"

    @property
    def import_staging_dir(self) -> Path:
        return self.staging_dir / "imports"

    @property
    def sources_root_dir(self) -> Path:
        return self.data_dir / "sources"

    @property
    def local_import_dir(self) -> Path:
        return self.sources_root_dir / "local-files" / "import"

    @property
    def fallback_assets_dir(self) -> Path:
        return self.data_dir / "fallback"


settings = Settings()

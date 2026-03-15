from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_DIR = Path(__file__).resolve().parents[2]
REPO_ROOT = BACKEND_DIR.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "SPF5000"
    app_version: str = "1.0.0"
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173", "http://127.0.0.1:5173"])

    data_dir: Path = BACKEND_DIR / "data"
    cache_dir: Path = BACKEND_DIR / "cache"
    log_dir: Path = BACKEND_DIR / "logs"
    database_path: Path = BACKEND_DIR / "data" / "spf5000.ddb"
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

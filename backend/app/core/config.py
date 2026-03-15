from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_name: str = "SPF5000"
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = True
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])

    data_dir: Path = Path("./data")
    cache_dir: Path = Path("./cache")
    database_path: Path = Path("./data/spf5000.ddb")


settings = Settings()

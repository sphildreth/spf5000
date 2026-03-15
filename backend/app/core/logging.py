from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler

from app.core.config import settings


LOG_FORMAT = "%(asctime)s %(levelname)s [%(name)s] %(message)s"


def configure_logging() -> None:
    settings.log_dir.mkdir(parents=True, exist_ok=True)

    root_logger = logging.getLogger()
    if getattr(root_logger, "_spf5000_configured", False):
        return

    root_logger.setLevel(logging.DEBUG if settings.debug else logging.INFO)

    formatter = logging.Formatter(LOG_FORMAT)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)

    file_handler = RotatingFileHandler(
        settings.log_dir / "spf5000.log",
        maxBytes=1_048_576,
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)

    root_logger.handlers.clear()
    root_logger.addHandler(stream_handler)
    root_logger.addHandler(file_handler)
    root_logger._spf5000_configured = True  # type: ignore[attr-defined]

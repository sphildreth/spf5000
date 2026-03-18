from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
import sys

import structlog

from app.core.config import settings


LOG_FORMAT = "%(message)s"


def _resolve_log_level() -> int:
    configured = getattr(logging, settings.log_level.upper(), None)
    if isinstance(configured, int):
        if settings.debug and configured == logging.INFO:
            return logging.DEBUG
        return configured
    return logging.DEBUG if settings.debug else logging.INFO


def configure_logging() -> None:
    settings.log_dir.mkdir(parents=True, exist_ok=True)

    root_logger = logging.getLogger()
    if getattr(root_logger, "_spf5000_configured", False):
        return

    root_logger.setLevel(_resolve_log_level())

    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setFormatter(logging.Formatter(LOG_FORMAT))
    root_logger.addHandler(console_handler)

    file_handler = RotatingFileHandler(
        settings.log_dir / "spf5000.log",
        maxBytes=1_048_576,
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT))
    root_logger.addHandler(file_handler)

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M:%S"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    root_logger._spf5000_configured = True  # type: ignore[attr-defined]


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)

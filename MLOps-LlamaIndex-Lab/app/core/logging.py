"""
Logging configuration for the application.

Provides a single ``get_logger`` helper so every module gets a
consistently formatted logger.
"""

import logging
import sys

from app.core.config import settings


def get_logger(name: str) -> logging.Logger:
    """Return a logger with a standard format attached to *stdout*."""
    logger = logging.getLogger(name)

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    logger.setLevel(settings.log_level.upper())
    return logger

"""Emit the application's structured logs when the API runs under a server."""

from __future__ import annotations

import logging
import os

_PACKAGE_LOGGER = "ayorai_attractor"
_HANDLER_MARKER = "_ayorai_attractor_handler"
_ALLOWED_LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")
_DEFAULT_LEVEL = "INFO"


def resolve_log_level() -> int:
    """Return the configured level, rejecting unknown names."""
    raw = os.getenv("ATTRACTOR_LOG_LEVEL", _DEFAULT_LEVEL).strip().upper() or _DEFAULT_LEVEL
    if raw not in _ALLOWED_LEVELS:
        raise ValueError(f"ATTRACTOR_LOG_LEVEL must be one of {', '.join(_ALLOWED_LEVELS)}")
    return {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL,
    }[raw]


def configure_logging() -> None:
    """Attach one stderr handler to the package logger, idempotently.

    Records still propagate, so host applications and test log capture keep working.
    """
    level = resolve_log_level()
    logger = logging.getLogger(_PACKAGE_LOGGER)
    logger.setLevel(level)
    if any(getattr(handler, _HANDLER_MARKER, False) for handler in logger.handlers):
        return
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(message)s"))
    setattr(handler, _HANDLER_MARKER, True)
    logger.addHandler(handler)

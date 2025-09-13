"""Shared logger utility for all services.

Provides a consistent get_logger function that can be used across all services.
Auto-configures logging on first use if not already configured.
"""

from __future__ import annotations

import logging

_configured = False


def get_logger(name: str, auto_configure: bool = True) -> logging.Logger:
    """Get a preconfigured structured logger.

    Args:
        name: Logger name (usually module name)
        auto_configure: Whether to auto-configure logging on first use

    Returns:
        Configured logger instance
    """
    global _configured

    if auto_configure and not _configured:
        _configure_minimal_logging()
        _configured = True

    logger = logging.getLogger(name)
    logger.propagate = True
    return logger


def _configure_minimal_logging():
    """Minimal logging configuration as fallback."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )


def is_configured() -> bool:
    """Check if logging has been configured."""
    return _configured


def mark_configured():
    """Mark logging as configured (called by shared.logging.json.configure_logging)."""
    global _configured
    _configured = True

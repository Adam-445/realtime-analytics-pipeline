"""Deprecated local logging config; re-export shared configure_logging.

This preserves backward compatibility for existing imports while ensuring
consistent logging structure across services.
"""

from __future__ import annotations

from src.core.config import settings

try:  # pragma: no cover
    from shared.logging.json import configure_logging as _shared_configure_logging
except Exception:  # noqa: pragma: no cover
    _shared_configure_logging = None  # type: ignore

import logging


def configure_logging():  # type: ignore
    if _shared_configure_logging:
        return _shared_configure_logging(
            service="processing",
            level=settings.app_log_level,
            environment=settings.app_environment,
            redaction_patterns=settings.app_log_redaction_patterns,
        )
    # Fallback basic config
    logging.basicConfig(
        level=getattr(logging, settings.app_log_level.upper(), logging.INFO)
    )
    return logging.getLogger()

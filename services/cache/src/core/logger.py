from __future__ import annotations

import logging
from typing import Iterable

from .config import settings

try:  # pragma: no cover
    from shared.logging.json import configure_logging as _shared_configure_logging
except Exception:  # noqa: pragma: no cover
    _shared_configure_logging = None  # type: ignore


class RedactingFilter(logging.Filter):
    def __init__(self, patterns: Iterable[str]):
        super().__init__()
        self.patterns = [p.lower() for p in patterns]

    def filter(self, record: logging.LogRecord) -> bool:  # type: ignore[override]
        try:
            msg = record.getMessage().lower()
            if any(p in msg for p in self.patterns):
                record.msg = "[REDACTED SENSITIVE LOG CONTENT]"
                record.args = ()
        except Exception:  # pragma: no cover - safety
            pass
        return True


_configured = False


def configure_logging():
    global _configured
    if _configured:
        return
    if _shared_configure_logging is not None:
        _shared_configure_logging(
            service="cache",
            level=settings.app_log_level,
            environment=settings.app_environment,
            redaction_patterns=settings.app_log_redaction_patterns,
        )
    else:  # fallback minimal config
        logging.basicConfig(
            level=getattr(logging, settings.app_log_level.upper(), logging.INFO)
        )
    # Attach redaction filter at root so it applies to all handlers
    root = logging.getLogger()
    for h in root.handlers:
        h.addFilter(RedactingFilter(settings.app_log_redaction_patterns))
    _configured = True


def get_logger(name: str) -> logging.Logger:  # backward compatibility
    configure_logging()
    return logging.getLogger(name)

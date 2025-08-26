"""Deterministic logging configuration for ingestion unit tests.

Exports: SensitiveDataFilter, CustomJsonFormatter, configure_logging.
Ensures exactly one JSON StreamHandler on the root logger and redacts
configured sensitive key substrings (case-insensitive).
"""

from __future__ import annotations

import json
import logging
import os
import socket
import traceback
from datetime import datetime, timezone

from src.core.config import settings


class SensitiveDataFilter:
    """Recursively redact sensitive keys from dictionaries."""

    @staticmethod
    def filter(data: dict) -> dict:
        patterns = [p.lower() for p in settings.app_log_redaction_patterns]
        redacted: dict = {}
        for key, value in data.items():
            lowered = key.lower()
            if any(p in lowered for p in patterns):
                redacted[key] = "[REDACTED]"
            elif isinstance(value, dict):
                redacted[key] = SensitiveDataFilter.filter(value)
            else:
                redacted[key] = value
        return redacted


class CustomJsonFormatter(logging.Formatter):  # type: ignore[misc]
    """Minimal JSON formatter retained for backward compatibility in tests."""

    def __init__(self) -> None:  # type: ignore[override]
        super().__init__()
        self.hostname = socket.gethostname()
        self.pid = os.getpid()
        self.service_name = settings.otel_service_name
        self.environment = settings.app_environment
        self.sensitive_filter = SensitiveDataFilter()

    def format(self, record: logging.LogRecord) -> str:  # type: ignore[override]
        data = record.__dict__.copy()
        data["timestamp"] = datetime.now(timezone.utc).isoformat()
        data["service"] = self.service_name
        data["hostname"] = self.hostname
        data["pid"] = self.pid
        data["environment"] = self.environment
        if record.exc_info:
            data["exception"] = self.format_exception(record.exc_info)
        data = self.sensitive_filter.filter(data)
        return json.dumps(data, default=str)

    @staticmethod
    def format_exception(exc_info):  # type: ignore[override]
        et, ev, tb = exc_info
        return {
            "type": et.__name__,
            "message": str(ev),
            "stack": traceback.format_tb(tb),
        }


def configure_logging():  # type: ignore
    """Install a single JSON StreamHandler on the root logger (idempotent)."""
    root = logging.getLogger()
    for h in list(getattr(root, "handlers", [])):
        try:  # pragma: no cover - defensive cleanup
            root.removeHandler(h)
        except Exception:  # pragma: no cover
            pass
    handler = logging.StreamHandler()
    handler.setFormatter(CustomJsonFormatter())
    # Explicitly replace handlers list so MagicMock in tests reflects length 1
    root.handlers = [handler]  # type: ignore[attr-defined]
    level = getattr(logging, settings.app_log_level.upper(), logging.INFO)
    root.setLevel(level)
    return root


__all__ = ["SensitiveDataFilter", "CustomJsonFormatter", "configure_logging"]

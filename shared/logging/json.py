"""Unified JSON logging utilities.

Provides a single CustomJsonFormatter and configure_logging used across
services. Matches ingestion unit test expectations (attributes:
`sensitive_filter`, `format_exception`).
"""

from __future__ import annotations

import json
import logging
import os
import socket
import traceback
from datetime import datetime, timezone
from typing import Iterable


class SensitiveDataFilter:
    def __init__(self, patterns: Iterable[str]):
        self.patterns = [p.lower() for p in patterns]

    def filter(self, data: dict) -> dict:  # shallow copy then recursive
        out = {}
        for k, v in data.items():
            lk = k.lower()
            if any(p in lk for p in self.patterns):
                out[k] = "[REDACTED]"
            elif isinstance(v, dict):
                out[k] = self.filter(v)
            else:
                out[k] = v
        return out


class CustomJsonFormatter(logging.Formatter):  # type: ignore[misc]
    def __init__(
        self,
        service: str,
        environment: str,
        redaction_patterns: Iterable[str],
    ):
        super().__init__()
        self.hostname = socket.gethostname()
        self.pid = os.getpid()
        self.service_name = service
        self.environment = environment
        self.sensitive_filter = SensitiveDataFilter(redaction_patterns)

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


def configure_logging(
    service: str,
    environment: str,
    level: str,
    redaction_patterns: Iterable[str],
):
    handler = logging.StreamHandler()
    handler.setFormatter(CustomJsonFormatter(service, environment, redaction_patterns))
    root = logging.getLogger()
    root.handlers = [handler]  # deterministic single handler
    root.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Mark logger as configured for shared logger utility
    try:
        from shared.logging.logger import mark_configured

        mark_configured()
    except ImportError:
        pass  # shared logger not available

    return root


__all__ = [
    "CustomJsonFormatter",
    "configure_logging",
    "SensitiveDataFilter",
]

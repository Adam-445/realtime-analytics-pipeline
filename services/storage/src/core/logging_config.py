import json
import logging
import os
import socket
import traceback
from datetime import datetime, timezone

from opentelemetry import trace
from opentelemetry.propagate import inject
from pythonjsonlogger.json import JsonFormatter
from src.core.config import settings


class SensitiveDataFilter:
    """Filter sensitive data from logs"""

    @staticmethod
    def filter(data: dict) -> dict:
        """Replace sensitive values with '[REDACTED]'"""
        filtered = data.copy()
        for key, value in data.items():
            key_lower = key.lower()
            if any(sens in key_lower for sens in settings.app_log_redaction_patterns):
                filtered[key] = "[REDACTED]"
            elif isinstance(value, dict):
                filtered[key] = SensitiveDataFilter.filter(value)
        return filtered


class CustomJsonFormatter(JsonFormatter):
    """Production-grade JSON formatter with OTel integration"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.hostname = socket.gethostname()
        self.pid = os.getpid()
        self.sensitive_filter = SensitiveDataFilter()

        # Cache service name
        self.service_name = settings.otel_service_name
        self.environment = settings.app_environment

    def format(self, record):
        record_dict = record.__dict__.copy()

        # Add standard fields
        record_dict["timestamp"] = datetime.now(timezone.utc).isoformat()
        record_dict["service"] = self.service_name
        record_dict["hostname"] = self.hostname
        record_dict["pid"] = self.pid
        record_dict["environment"] = self.environment

        self.add_otel_context(record_dict)

        if record.exc_info:
            record_dict["exception"] = self.format_exception(record.exc_info)

        record_dict = self.sensitive_filter.filter(record_dict)

        return json.dumps(record_dict, default=str)

    def format_exception(self, exc_info):
        """Format exception with stack trace"""
        ex_type, ex_value, ex_traceback = exc_info
        return {
            "type": ex_type.__name__,
            "message": str(ex_value),
            "stack": traceback.format_tb(ex_traceback),
        }

    def add_otel_context(self, record_dict):
        """Add OpenTelemetry context efficiently"""
        span = trace.get_current_span()
        if not span or not span.get_span_context().is_valid:
            return

        ctx = span.get_span_context()
        record_dict["trace_id"] = format(ctx.trace_id, "032x")
        record_dict["span_id"] = format(ctx.span_id, "016x")
        record_dict["trace_flags"] = format(ctx.trace_flags, "02d")

        # For W3C trace context propagation
        carrier = {}
        inject(carrier)
        record_dict["traceparent"] = carrier.get("traceparent", "")


def configure_logging():
    """Configure structured logging for the service"""
    formatter = CustomJsonFormatter()

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    logger = logging.getLogger()
    logger.handlers = [console_handler]

    # Set log level from config
    log_level = getattr(logging, settings.app_log_level.upper(), logging.INFO)
    logger.setLevel(log_level)

    return logger

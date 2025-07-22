import logging
import os
import socket
from datetime import datetime, timezone

from opentelemetry import trace
from pythonjsonlogger.json import JsonFormatter
from src.core.config import settings


class CustomJsonFormatter(JsonFormatter):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.hostname = socket.gethostname()
        self.pid = os.getpid()

    def format(self, record):
        # Ensure the record has a valid timestamp in ISO 8601 format
        if not hasattr(record, "created"):
            record.created = datetime.now(timezone.utc).timestamp()

        # Format timestamp in ISO 8601
        iso_time = datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat()

        # Add exception details if present
        if record.exc_info:
            exc_text = self.formatException(record.exc_info)
            setattr(record, "_formatted_exc", exc_text)

        setattr(record, "_iso_timestamp", iso_time)
        return super().format(record)

    def add_fields(self, log_record, record, message_dict):
        super().add_fields(log_record, record, message_dict)
        log_record["timestamp"] = getattr(record, "_iso_timestamp")
        log_record["service"] = settings.otel_service_name
        log_record["hostname"] = self.hostname
        log_record["pid"] = self.pid

        # Add environment info
        log_record["environment"] = settings.app_environment

        # Add exception info if present
        if record.exc_info and hasattr(record, "_formatted_exc"):
            log_record["exception"] = getattr(record, "_formatted_exc")

        # Add Opentelemetry context if available
        span = trace.get_current_span()
        if span and span.get_span_context().is_valid:
            ctx = span.get_span_context()
            log_record["trace_id"] = format(ctx.trace_id, "032x")
            log_record["span_id"] = format(ctx.span_id, "016x")


def configure_logging():
    format_string = (
        "%(message)s %(levelname)s %(name)s " "%(processName)s %(funcName)s %(lineno)d"
    )

    formatter = CustomJsonFormatter(format_string)

    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    logger = logging.getLogger()

    logger.handlers = [handler]

    logger.setLevel(getattr(logging, settings.app_log_level.upper()))

    logging.getLogger("asyncio").setLevel(logging.INFO)

    return logger

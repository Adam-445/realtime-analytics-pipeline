import logging

from opentelemetry import trace
from pythonjsonlogger.json import JsonFormatter
from src.core.config import settings


class CustomJsonFormatter(JsonFormatter):
    def add_fields(self, log_record, record, message_dict):
        super().add_fields(log_record, record, message_dict)
        log_record["service"] = settings.otel_service_name
        log_record["level"] = record.levelname
        log_record["logger"] = record.name

        # Add Opentelemetry context if available
        span = trace.get_current_span()
        if span and span.get_span_context().is_valid:
            ctx = span.get_span_context()
            log_record["trace_id"] = format(ctx.trace_id, "032x")
            log_record["span_id"] = format(ctx.span_id, "016x")


def configure_logging():
    formatter = CustomJsonFormatter("%(asctime)s %(levelname)s %(name)s %(message)s")

    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    logger = logging.getLogger()
    logger.handlers = [handler]
    logger.setLevel(getattr(logging, settings.app_log_level.upper()))

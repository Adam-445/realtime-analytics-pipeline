import logging
from typing import List

from .config import settings


class RedactingFilter(logging.Filter):
    def __init__(self, patterns: List[str]):
        super().__init__()
        self.patterns = patterns

    def filter(self, record: logging.LogRecord) -> bool:  # type: ignore[override]
        msg = record.getMessage()
        lower = msg.lower()
        for p in self.patterns:
            if p in lower:
                record.msg = "[REDACTED SENSITIVE LOG CONTENT]"
                record.args = ()  # prevent formatting with stale args
                break
        return True


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(getattr(logging, settings.app_log_level.upper(), logging.INFO))
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
                datefmt="%Y-%m-%dT%H:%M:%S%z",
            )
        )
        handler.addFilter(RedactingFilter(settings.app_log_redaction_patterns))
        logger.addHandler(handler)
    return logger

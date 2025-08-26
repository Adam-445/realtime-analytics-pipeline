"""Processing service logger shim.

Retained for backward compatibility; delegates to standard logging after
shared configure_logging is invoked in main entrypoint.
"""

from __future__ import annotations

import logging


def get_logger(name: str) -> logging.Logger:  # type: ignore
    return logging.getLogger(name)

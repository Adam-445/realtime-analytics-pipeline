"""Deprecated legacy logging config for storage; use shared.logging.formatting.

Retained to avoid breaking imports while refactor is in progress.
"""

from shared.logging.formatting import configure_logging  # re-export

__all__ = ["configure_logging"]

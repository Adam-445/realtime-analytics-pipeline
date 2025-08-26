"""Deprecated legacy entrypoint. Use src.app instead.

Maintained temporarily for backward compatibility with existing Docker
Entrypoint or scripts referencing batch_processor.py.
"""

from src.app import main  # noqa: F401

"""Deprecated module.

Use `shared.logging.json` instead which provides `CustomJsonFormatter` and
`configure_logging`. This shim remains to avoid breaking any lingering imports
until full cleanup. It simply re-exports the new implementations.
"""

from .json import (  # noqa: F401
    CustomJsonFormatter,
    SensitiveDataFilter,
    configure_logging,
)

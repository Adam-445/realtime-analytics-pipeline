"""Unified metrics helpers.

Provides thin wrappers around prometheus_client primitives with (optional)
service name prefixing and basic naming validation. Keeps registry default so
multi-process mode can be configured externally.

Previous `metric_factory` is retained for backwards compatibility but should
be replaced with direct helper functions.
"""

from __future__ import annotations

import re

from prometheus_client import Counter, Gauge, Histogram

_NAME_RE = re.compile(r"^[a-z_][a-z0-9_]*$")


def _validate(name: str) -> str:
    if not _NAME_RE.match(name):  # pragma: no cover - simple guard
        raise ValueError(
            f"Invalid metric name '{name}'. Use snake_case alphanumerics/underscores."
        )
    return name


def _prefix(name: str, service: str | None) -> str:
    if service and not name.startswith(service + "_"):
        return f"{service}_{name}"
    return name


def get_counter(name: str, documentation: str, service: str | None = None) -> Counter:
    return Counter(_validate(_prefix(name, service)), documentation)


def get_histogram(
    name: str,
    documentation: str,
    service: str | None = None,
    buckets: list[float] | None = None,
) -> Histogram:
    full_name = _validate(_prefix(name, service))
    if buckets is None:
        return Histogram(full_name, documentation)
    return Histogram(full_name, documentation, buckets=buckets)


def get_gauge(name: str, documentation: str, service: str | None = None) -> Gauge:
    return Gauge(_validate(_prefix(name, service)), documentation)


def metric_factory(service: str):  # pragma: no cover - deprecated path
    """Deprecated. Prefer get_counter/get_histogram/get_gauge with service arg."""

    def counter(name: str, documentation: str) -> Counter:
        return get_counter(name, documentation, service)

    def histogram(
        name: str, documentation: str, buckets: list[float] | None = None
    ) -> Histogram:
        return get_histogram(name, documentation, service, buckets)

    def gauge(name: str, documentation: str) -> Gauge:
        return get_gauge(name, documentation, service)

    return counter, histogram, gauge


__all__ = [
    "get_counter",
    "get_histogram",
    "get_gauge",
    "metric_factory",  # deprecated
]

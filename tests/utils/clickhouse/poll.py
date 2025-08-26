import time
from typing import Any

from clickhouse_driver.errors import ServerException


def poll_for_data(
    clickhouse_client: Any,
    query: str,
    params: dict[str, Any] | None = None,
    max_wait_time: float = 20.0,
    poll_interval: float = 2.0,
    expected_count: int = 1,
    verbose: bool = False,
) -> list[tuple]:
    """Poll ClickHouse until at least expected_count rows or timeout.

    The function is intentionally silent by default to keep test output clean.
    Set verbose=True for ad‑hoc debugging.
    """
    params = {} if params is None else params  # avoid mutable default

    start = time.time()
    while time.time() - start < max_wait_time:
        try:
            result = clickhouse_client.execute(query, params)
        except ServerException as se:
            # Code 60: table not yet created / storage not ready; retry
            if getattr(se, "code", None) == 60:
                time.sleep(poll_interval)
                continue
            raise
        if len(result) >= expected_count:
            if verbose:
                print(
                    f"poll_for_data: found {len(result)} rows \
                      (expected {expected_count})"
                )
            return result
        if verbose:
            print(
                f"poll_for_data: have {len(result)} < {expected_count}; \
                    sleeping {poll_interval}s"
            )
        time.sleep(poll_interval)

    raise TimeoutError(
        f"Timed out after {max_wait_time}s: query={query!r}, params={params!r}"
    )

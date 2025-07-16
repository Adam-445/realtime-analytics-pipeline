import time
from typing import Any


def poll_for_data(
    clickhouse_client: Any,
    query: str,
    params: dict[str, Any] | None = None,
    max_wait_time: float = 20.0,
    poll_interval: float = 2.0,
    expected_count: int = 1,
) -> list[tuple]:
    """
    Polls ClickHouse until at least `expected_count` rows are returned or timeout.
    """
    # avoid mutable-default
    params = {} if params is None else params

    start = time.time()
    while time.time() - start < max_wait_time:
        result = clickhouse_client.execute(query, params)
        if len(result) >= expected_count:
            print(f"Success! Found {len(result)} rows.")
            return result

        print(
            f"Found {len(result)} rows, "
            f"waiting for {expected_count}. "
            f"Sleeping {poll_interval}s…"
        )
        time.sleep(poll_interval)

    raise TimeoutError(
        f"Timed out after {max_wait_time}s: " f"query={query!r}, params={params!r}"
    )

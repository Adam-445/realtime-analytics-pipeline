from typing import Any, Dict, Literal, TypedDict


class Operation(TypedDict):
    """Internal batched write operation.

    Fields:
        type: Operation category ("event" | "perf").
        window_start: Start timestamp (ms) for the metrics aggregation window.
        fields: Flattened metrics fields to store in Redis hash.
    """

    type: Literal["event", "perf"]
    window_start: int
    fields: Dict[str, Any]

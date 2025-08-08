from math import floor
from typing import List


def bucket_start(timestamp_seconds: float, granularity_seconds: int) -> int:
    return int(floor(timestamp_seconds / granularity_seconds) * granularity_seconds)


def enumerate_bucket_starts(
    end_timestamp_seconds: int,
    window_seconds: int,
    granularity_seconds: int,
) -> List[int]:
    start = end_timestamp_seconds - window_seconds + granularity_seconds
    if start < 0:
        start = 0
    buckets = []
    t = bucket_start(start, granularity_seconds)
    end_bucket = bucket_start(end_timestamp_seconds, granularity_seconds)
    while t <= end_bucket:
        buckets.append(t)
        t += granularity_seconds
    return buckets

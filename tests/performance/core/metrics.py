from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional


@dataclass
class Metrics:
    # Basic
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0

    # Timing
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    test_duration: float = 0.0

    # Latency (ms)
    response_times: List[float] = field(default_factory=list)
    min_latency: float = 0.0
    max_latency: float = 0.0
    avg_latency: float = 0.0
    p50_latency: float = 0.0
    p95_latency: float = 0.0
    p99_latency: float = 0.0

    # Throughput
    actual_rps: float = 0.0
    peak_rps: float = 0.0

    # Errors
    error_rate: float = 0.0
    connection_errors: int = 0
    timeout_errors: int = 0
    http_errors: Dict[int, int] = field(default_factory=dict)

    def finalize(self):
        if self.start_time and self.end_time:
            self.test_duration = (self.end_time - self.start_time).total_seconds()
        if self.test_duration > 0:
            self.actual_rps = self.total_requests / self.test_duration
        if self.total_requests > 0:
            self.error_rate = (self.failed_requests / self.total_requests) * 100
        if self.response_times:
            self.response_times.sort()
            self.min_latency = min(self.response_times)
            self.max_latency = max(self.response_times)
            self.avg_latency = statistics.mean(self.response_times)
            self.p50_latency = statistics.median(self.response_times)
            n = len(self.response_times)
            if n > 1:
                self.p95_latency = self.response_times[int(0.95 * n)]
                self.p99_latency = self.response_times[int(0.99 * n)]
            else:
                self.p95_latency = self.avg_latency
                self.p99_latency = self.avg_latency

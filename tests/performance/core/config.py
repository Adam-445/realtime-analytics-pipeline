from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import List


@dataclass
class TestConfig:
    # Load params
    target_rps: int = 1000
    duration_seconds: int = 60
    max_concurrent_connections: int = 1000
    connection_pool_size: int = 500

    # Endpoints (local run by default)
    ingestion_url: str = os.getenv("INGESTION_URL", "http://localhost:8000")
    cache_url: str = os.getenv("CACHE_URL", "http://localhost:8080")

    # Optional data knobs
    event_types: List[str] = field(
        default_factory=lambda: [
            "page_view",
            "click",
            "conversion",
            "add_to_cart",
        ]
    )

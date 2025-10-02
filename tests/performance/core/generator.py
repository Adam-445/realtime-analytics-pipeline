from __future__ import annotations

import random
from typing import Dict

from performance.core.config import TestConfig


class EventGenerator:
    def __init__(self, config: TestConfig):
        self.config = config
        self.user_pool = [f"perf-user-{i}" for i in range(10000)]
        self.session_pool = [f"perf-session-{i}" for i in range(5000)]
        self.urls = [f"https://example.com/page_{i}" for i in range(100)]
        self.referrers = [f"https://google.com/search?q=term_{i}" for i in range(50)]
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            (
                "Mozilla/5.0 (iPhone; CPU iPhone OS 14_7_1 like Mac OS X) "
                "AppleWebKit/605.1.15"
            ),
            "Mozilla/5.0 (Android 11; Mobile; rv:68.0) Gecko/68.0 Firefox/88.0",
        ]

    def generate_event(self) -> Dict:
        return {
            "event": {
                "type": random.choice(self.config.event_types),
            },
            "user": {
                "id": random.choice(self.user_pool),
            },
            "device": {
                "user_agent": random.choice(self.user_agents),
                "screen_width": random.choice([1920, 1366, 1280]),
                "screen_height": random.choice([1080, 768, 720]),
            },
            "context": {
                "url": random.choice(self.urls),
                "session_id": random.choice(self.session_pool),
                "referrer": random.choice(self.referrers),
            },
            "metrics": {
                "load_time": random.randint(50, 2000),
                "interaction_time": random.randint(100, 5000),
            },
            "properties": {
                "page_category": random.choice(["home", "product", "checkout", "blog"]),
                "campaign_id": f"camp_{random.randint(1, 10)}",
                "ab_test_variant": random.choice(["A", "B", "control"]),
            },
        }

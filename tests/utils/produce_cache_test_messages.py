#!/usr/bin/env python
"""Produce synthetic metric windows to Kafka for cache smoke testing.

Usage (inside repo root with docker-compose running):
  python tests/utils/produce_cache_test_messages.py
"""
import asyncio
import json
import random
import time

from aiokafka import AIOKafkaProducer

BOOTSTRAP = "127.0.0.1:9092"  # external listener from host
EVENT_TOPIC = "event_metrics"
PERF_TOPIC = "performance_metrics"

EVENT_TYPES = ["page_view", "click", "signup"]
DEVICE_CATEGORIES = ["desktop", "mobile", "tablet"]


def epoch_ms() -> int:
    return int(time.time() * 1000) // 60000 * 60000  # align to minute


async def produce():
    producer = AIOKafkaProducer(bootstrap_servers=BOOTSTRAP)
    await producer.start()
    try:
        base_ts = epoch_ms()
        for i in range(3):
            window_ts = base_ts + i * 60000
            # event metrics
            for et in EVENT_TYPES:
                payload = {
                    "window_start": window_ts,
                    "event_type": et,
                    "event_count": random.randint(50, 500),
                    "user_count": random.randint(10, 200),
                }
                await producer.send_and_wait(
                    EVENT_TOPIC, value=json.dumps(payload).encode()
                )
            # performance metrics
            for dc in DEVICE_CATEGORIES:
                payload = {
                    "window_start": window_ts,
                    "device_category": dc,
                    "avg_load_time": round(random.uniform(0.5, 2.5), 3),
                    "p95_load_time": round(random.uniform(1.0, 4.0), 3),
                }
                await producer.send_and_wait(
                    PERF_TOPIC, value=json.dumps(payload).encode()
                )
        print("Produced synthetic metric windows.")
    finally:
        await producer.stop()


if __name__ == "__main__":
    asyncio.run(produce())

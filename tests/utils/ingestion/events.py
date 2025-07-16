import time
import uuid
from typing import Optional

import requests


def send_event(
    event_payload: dict,
    timestamp_override: Optional[int] = None,
    api_url: str = "http://ingestion:8000/v1/analytics/track",
) -> int:
    """
    Send a test event to the API endpoint, optionally overriding the timestamp.

    Returns the timestamp used for the event.
    """
    # Determine event timestamp
    event_timestamp = (
        timestamp_override
        if timestamp_override is not None
        else int(time.time() * 1000)
    )
    event_payload.setdefault("timestamp", event_timestamp)

    response = requests.post(api_url, json=event_payload)
    if response.status_code != 202:
        raise Exception(f"Event sending failed: {response.status_code}")

    return event_timestamp

def create_test_event(
    event_type: str = "page_view",
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    load_time: int = 120,
    timestamp: Optional[int] = None,
) -> dict:
    """
    Create a standardized test event payload.
    """
    ts = timestamp or int(time.time() * 1000)
    return {
        "event": {"type": event_type},
        "user": {"id": user_id or f"test-user-{uuid.uuid4()}"},
        "context": {
            "url": "http://example.com/test-page",
            "referrer": None,
            "ip_address": "192.168.1.1",
            "session_id": session_id or f"test-session-{uuid.uuid4()}",
        },
        "device": {
            "user_agent": "E2E-Test-Agent",
            "screen_width": 1920,
            "screen_height": 1080,
        },
        "properties": {"test_id": str(uuid.uuid4())},
        "metrics": {"load_time": load_time, "interaction_time": 800},
        "timestamp": ts,
    }


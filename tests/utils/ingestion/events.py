import time
import uuid

import requests


def send_event(
    event_payload: dict,
    timestamp_override: int | None = None,
    api_url: str = "http://ingestion:8000/v1/analytics/track",
    retries: int = 10,
    backoff_seconds: float = 0.5,
    timeout_seconds: float = 2.0,
) -> int:
    """
    Send a test event to the API endpoint with simple retry/backoff,
    optionally overriding the timestamp.

    Returns the timestamp used for the event.
    """
    # Determine event timestamp
    event_timestamp = (
        timestamp_override
        if timestamp_override is not None
        else int(time.time() * 1000)
    )
    event_payload.setdefault("timestamp", event_timestamp)

    last_err: Exception | None = None
    for attempt in range(1, max(1, retries) + 1):
        try:
            response = requests.post(
                api_url, json=event_payload, timeout=timeout_seconds
            )
            if response.status_code != 202:
                # Treat non-202 as retryable for early attempts to ride out startup
                last_err = Exception(
                    f"Event sending failed: HTTP {response.status_code}"
                )
            else:
                return event_timestamp
        except requests.RequestException as e:
            last_err = e

        # Backoff if not last attempt
        if attempt < retries:
            time.sleep(backoff_seconds)
        else:
            break

    # Exhausted retries
    raise last_err or Exception("Event sending failed after retries")


def create_test_event(
    event_type: str = "page_view",
    user_id: str | None = None,
    session_id: str | None = None,
    load_time: int = 120,
    timestamp: int | None = None,
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
            "user_agent": "Test-Agent",
            "screen_width": 1920,
            "screen_height": 1080,
        },
        "properties": {"test_id": str(uuid.uuid4())},
        "metrics": {"load_time": load_time, "interaction_time": 800},
        "timestamp": ts,
    }

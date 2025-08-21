import random
import time
import uuid
from typing import Any, Dict

import requests


def create_test_event(
    event_type: str = "page_view",
    user_id: str | None = None,
    session_id: str | None = None,
    load_time: int | None = None,
    user_agent: str | None = None,
    url: str | None = None,
    referrer: str | None = None,
    timestamp_override: int | None = None,
) -> Dict[str, Any]:
    """
    Create a test event payload matching your ingestion API structure.

    Args:
        event_type: Type of event (page_view, click, conversion, add_to_cart)
        user_id: User identifier
        session_id: Session identifier
        load_time: Page load time in milliseconds
        user_agent: Browser user agent string
        url: Page URL
        referrer: Referrer URL
        timestamp_override: Override timestamp (milliseconds since epoch)

    Returns:
        Event payload dictionary
    """
    if not user_id:
        user_id = f"test-user-{uuid.uuid4()}"
    if not session_id:
        session_id = f"test-session-{uuid.uuid4()}"
    if load_time is None:
        load_time = random.randint(100, 3000)
    if not user_agent:
        user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    if not url:
        url = f"https://example.com/page_{random.randint(1, 100)}"
    if not referrer:
        referrer = f"https://google.com/search?q=test_{random.randint(1, 10)}"

    timestamp = timestamp_override or int(time.time() * 1000)

    # Create event matching your expected structure
    event = {
        "event": {
            "type": event_type,
            "timestamp": timestamp,
        },
        "user": {
            "id": user_id,
        },
        "device": {
            "user_agent": user_agent,
            "screen_width": random.choice([1920, 1366, 1280, 768]),
            "screen_height": random.choice([1080, 768, 720, 1024]),
        },
        "context": {
            "url": url,
            "session_id": session_id,
            "referrer": referrer,
        },
        "metrics": {
            "load_time": load_time,
            "interaction_time": random.randint(100, 5000),
        },
        "properties": {
            "page_category": random.choice(["home", "product", "checkout", "blog"]),
            "campaign_id": f"camp_{random.randint(1, 10)}",
            "ab_test_variant": random.choice(["A", "B", "control"]),
        },
    }

    return event


def send_event(
    event_payload: Dict[str, Any] | None = None,
    timestamp_override: int | None = None,
    ingestion_url: str = "http://ingestion:8000",
) -> int:
    """
    Send an event to the ingestion API.

    Args:
        event_payload: Event payload to send (if None, creates a default one)
        timestamp_override: Override timestamp for the event
        ingestion_url: Base URL of the ingestion service

    Returns:
        Timestamp when the event was sent

    Raises:
        requests.RequestException: If the API call fails
    """
    if event_payload is None:
        event_payload = create_test_event(timestamp_override=timestamp_override)
    elif timestamp_override:
        event_payload["event"]["timestamp"] = timestamp_override

    send_timestamp = int(time.time() * 1000)

    response = requests.post(
        f"{ingestion_url}/v1/analytics/track",
        json=event_payload,
        # headers={"Content-Type": "application/json"},
        timeout=30,
    )

    # Raise an exception for bad status codes
    response.raise_for_status()

    return send_timestamp


def send_multiple_events(
    count: int,
    event_type: str = "page_view",
    base_user_id: str | None = None,
    base_session_id: str | None = None,
    interval_ms: int = 1000,
    ingestion_url: str = "http://localhost:8000",
) -> list[Dict[str, Any]]:
    """
    Send multiple events with controlled timing.

    Args:
        count: Number of events to send
        event_type: Type of events to send
        base_user_id: Base user ID (will append numbers)
        base_session_id: Base session ID (will append numbers)
        interval_ms: Interval between events in milliseconds
        ingestion_url: Base URL of the ingestion service

    Returns:
        List of event metadata (user_id, session_id, timestamp)
    """
    if not base_user_id:
        base_user_id = f"bulk-user-{uuid.uuid4()}"
    if not base_session_id:
        base_session_id = f"bulk-session-{uuid.uuid4()}"

    sent_events = []
    base_timestamp = int(time.time() * 1000)

    for i in range(count):
        user_id = f"{base_user_id}-{i}"
        session_id = f"{base_session_id}-{i}"
        timestamp = base_timestamp + (i * interval_ms)

        event = create_test_event(
            event_type=event_type,
            user_id=user_id,
            session_id=session_id,
            timestamp_override=timestamp,
        )

        send_timestamp = send_event(event, ingestion_url=ingestion_url)

        sent_events.append(
            {
                "user_id": user_id,
                "session_id": session_id,
                "event_type": event_type,
                "sent_timestamp": send_timestamp,
                "event_timestamp": timestamp,
            }
        )

        # Small delay to avoid overwhelming the API
        if i < count - 1:
            time.sleep(interval_ms / 1000.0)

    return sent_events

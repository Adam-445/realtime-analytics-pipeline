import time
import uuid

import requests


def advance_watermark(api_url: str, future_seconds: int = 60):
    """
    Send a dummy event with a future timestamp to advance FLink's watermark.
    This triggers processing of events in completed windows

    Args:
        api_url: The api endpoint
        future_seconds: How far in the future to set the timestamp
    """
    future_timestamp = (int(time.time()) + future_seconds) * 1000

    watermark_event = {
        "event": {"type": "__watermark__"},
        "user": {"id": f"watermark_user_{uuid.uuid4()}"},
        "context": {
            "url": "https://example.com/home",
            "referrer": "https://google.com/",
            "ip_address": "192.168.1.1",
            "session_id": f"watermark_sess_{uuid.uuid4()}",
        },
        "device": {
            "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
            "screen_width": 1920,
            "screen_height": 1080,
        },
        "properties": {"test_type": "watermark_advancement"},
        "metrics": {"load_time": 200, "interaction_time": 800},
        "timestamp": future_timestamp,
    }

    response = requests.post(url=api_url, json=watermark_event)
    if response.status_code != 202:
        raise Exception(f"Watermark advancement failed: {response.status_code}")

    print(f"Watermark advanced by {future_seconds}")


def wait_for_window_and_advance_watermark(window_size_seconds: int, api_url: str):
    """
    Wait for a window to complete and then advance the watermark to trigger processing
    """
    print(f"Waiting {window_size_seconds + 2} seconds for window to close...")
    time.sleep(window_size_seconds + 2)

    print("Advancing watermark to trigger processing...")
    advance_watermark(api_url)

    # Give Flink a moment to process
    time.sleep(2)

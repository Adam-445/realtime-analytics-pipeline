import os
import time
import uuid

import pytest
import requests

from tests.tests_helpers import wait_for_window_and_advance_watermark

SESSION_GAP_SECONDS = int(os.environ.get("SESSION_GAP_SECONDS", "1800"))


def test_happy_path_page_view_event_is_processed(clickhouse_client):
    """
    Tests the full pipeline from ingestion to storage.
    """
    # Create a unique user and session ID for this test run
    user_id = f"test-user-{uuid.uuid4()}"
    session_id = f"test-session-{uuid.uuid4()}"

    event_payload = {
        "event": {"type": "page_view"},
        "user": {"id": user_id},
        "device": {
            "user_agent": "E2E-Test-Agent",
            "screen_width": 1920,
            "screen_height": 1080,
        },
        "context": {
            "url": "http://example.com/test-page",
            "referrer": None,
            "session_id": session_id,
        },
        "properties": {"test_id": str(uuid.uuid4())},
        "metrics": {"load_time": 120},
    }

    # Send the event to the ingestion service
    api_url = "http://ingestion:8000/v1/analytics/track"
    response = requests.post(api_url, json=event_payload)
    assert (
        response.status_code == 202
    ), f"API call failed with status: {response.status_code}"

    # Wait for window to close and advance watermark to trigger processing
    wait_for_window_and_advance_watermark(
        window_size_seconds=SESSION_GAP_SECONDS, api_url=api_url
    )

    # Now poll for the original event - it should be processed
    max_wait_time = 30  # Reduced since we triggered processing
    poll_interval = 3
    start_time = time.time()

    while time.time() - start_time < max_wait_time:
        query = "SELECT * FROM session_metrics WHERE user_id = %(user_id)s \
            AND session_id = %(session_id)s"
        params = {"user_id": user_id, "session_id": session_id}
        result = clickhouse_client.execute(query, params)
        print("RESULT ++++++\n", result)

        if result:
            print(f"Success! Found processed event in DB: {result}")
            assert len(result) == 1
            processed_session = result[0]
            assert processed_session[1] == user_id  # user_id at index 1
            return  # Test passed

        print(f"Data not found yet. Waiting {poll_interval}s...")
        time.sleep(poll_interval)

    pytest.fail(
        f"E2E test failed: Did not find processed data for \
            user {user_id} in {max_wait_time}s."
    )

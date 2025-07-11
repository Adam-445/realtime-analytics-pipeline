import os
import time
import uuid

import pytest
import requests

from tests.helpers.debug import debug_database_state
from tests.helpers.watermark import wait_for_window_and_advance_watermark

SESSION_GAP_SECONDS = int(os.environ.get("SESSION_GAP_SECONDS", "1800"))
METRICS_WINDOW_SIZE_SECONDS = int(os.environ.get("METRICS_WINDOW_SIZE_SECONDS", "60"))


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
        "metrics": {"load_time": 120, "interaction_time": 800},
        "timestamp": int(time.time() * 1000),
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
    max_wait_time = 20
    poll_interval = 2
    start_time = time.time()

    while time.time() - start_time < max_wait_time:
        query = "SELECT * FROM session_metrics WHERE user_id = %(user_id)s \
            AND session_id = %(session_id)s"
        params = {"user_id": user_id, "session_id": session_id}
        result = clickhouse_client.execute(query, params)

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


def test_event_aggregator_counts_multiple_events(clickhouse_client):
    """
    Tests that the EventAggregator JOb is correctly counting different event types
    within a single window
    """
    timestamp = int(time.time() * 1000)
    events_to_send = [
        {
            "event": {"type": event_type},
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
            "metrics": {"load_time": 120, "interaction_time": 800},
            "timestamp": timestamp,
        }
        for event_type, user_id, session_id in [
            ("page_view", "user-a", "session-a"),
            ("page_view", "user-b", "session-b"),
            ("click", "user-a", "session-a"),
            ("conversion", "user-c", "session-c"),
        ]
    ]

    api_url = "http://ingestion:8000/v1/analytics/track"

    for payload in events_to_send:
        response = requests.post(api_url, json=payload)
        assert (
            response.status_code == 202
        ), f"API call failed for event: {payload['event']['type']}"

    wait_for_window_and_advance_watermark(
        window_size_seconds=METRICS_WINDOW_SIZE_SECONDS, api_url=api_url
    )

    query = "SELECT event_type, event_count, user_count FROM event_metrics"

    max_wait_time = 20
    poll_interval = 2
    start_time = time.time()

    while time.time() - start_time < max_wait_time:
        results = clickhouse_client.execute(query)
        debug_database_state(
            clickhouse_client=clickhouse_client,
            print_tables=True,
            tables=["event_metrics"],
        )
        # we expect 3 rows: one for page view one for click, and one for coversion
        if len(results) >= 3:
            aggregated_data = {
                row[0]: {"events": row[1], "users": row[2]} for row in results
            }
            print(f"Sucess! Found aggregated data in DB: {aggregated_data}")

            assert aggregated_data["page_view"]["events"] == 2
            assert aggregated_data["page_view"]["users"] == 2  # user-a, user-b

            assert aggregated_data["click"]["events"] == 1
            assert aggregated_data["click"]["users"] == 1  # user-a

            assert aggregated_data["conversion"]["events"] == 1
            assert aggregated_data["conversion"]["users"] == 1  # user-c

            return  # Test passed

        print(f"Aggregated data not found yet. Waiting {poll_interval}s...")
        time.sleep(poll_interval)

    pytest.fail("E2E test failed: Did not find correctly aggregated metrics.")

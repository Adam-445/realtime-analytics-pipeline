import time
import uuid

from tests.utils.clickhouse.poll import poll_for_data
from tests.utils.ingestion.events import create_test_event, send_event


def test_happy_path_page_view_event_is_processed(
    clickhouse_client,
    test_config,
):
    """
    Tests full pipeline: send page_view event and verify session metrics in ClickHouse.
    """
    # Prepare identifiers
    user_id = f"test-user-{uuid.uuid4()}"
    session_id = f"test-session-{uuid.uuid4()}"

    # Create and send event
    event_payload = create_test_event(
        event_type="page_view",
        user_id=user_id,
        session_id=session_id,
    )
    event_timestamp = send_event(event_payload=event_payload)
    print(f"Sent event with timestamp: {event_timestamp}")

    # Wait for session window to complete
    time.sleep(test_config["session_gap_seconds"] + 1)

    # Query for the processed session
    query = """
    SELECT session_id, user_id, start_time, end_time, duration, page_count, device_category
    FROM session_metrics 
    WHERE user_id = %(user_id)s AND session_id = %(session_id)s
    """
    params = {"user_id": user_id, "session_id": session_id}

    result = poll_for_data(
        clickhouse_client=clickhouse_client,
        query=query,
        params=params,
        max_wait_time=test_config.get("max_wait_time", 20),
        poll_interval=test_config.get("poll_interval", 2),
        expected_count=1,
    )

    # Verify session data
    processed_session = result[0]
    assert processed_session[0] == session_id
    assert processed_session[1] == user_id
    assert processed_session[5] == 1
    assert processed_session[6] == "Desktop"


def test_event_aggregator_counts_multiple_events(clickhouse_client, test_config):
    """
    Tests that the EventAggregator correctly counts different event types within a single window.
    """
    # Use a consistent timestamp base for all events in the same window
    base_timestamp = int(time.time() * 1000)

    # Define test events with different types and users
    test_events = [
        ("page_view", "user-a", "session-a"),
        ("page_view", "user-b", "session-b"),
        ("click", "user-a", "session-a"),
        ("conversion", "user-c", "session-c"),
    ]

    # Send all events with timestamps in the same window
    for i, (event_type, user_id, session_id) in enumerate(test_events):
        event_payload = create_test_event(
            event_type=event_type, user_id=user_id, session_id=session_id
        )

        # Send events with slight timestamp differences but within same window
        send_event(
            event_payload,
            timestamp_override=base_timestamp + i * 1000,  # 1 second apart
        )

    # Wait for metrics window to complete
    time.sleep(test_config["metrics_window_size_seconds"] + 1)

    # Query for aggregated metrics
    query = """
    SELECT event_type, event_count, user_count 
    FROM event_metrics 
    ORDER BY event_type
    """

    result = poll_for_data(
        clickhouse_client=clickhouse_client,
        query=query,
        max_wait_time=test_config["max_wait_time"],
        poll_interval=test_config["poll_interval"],
        expected_count=3,  # expecting 3 different event types
    )

    # Convert to dict for easier assertions
    aggregated_data = {row[0]: {"events": row[1], "users": row[2]} for row in result}

    # Verify aggregation results
    assert aggregated_data["page_view"]["events"] == 2
    assert aggregated_data["page_view"]["users"] == 2  # user-a, user-b

    assert aggregated_data["click"]["events"] == 1
    assert aggregated_data["click"]["users"] == 1  # user-a

    assert aggregated_data["conversion"]["events"] == 1
    assert aggregated_data["conversion"]["users"] == 1  # user-c

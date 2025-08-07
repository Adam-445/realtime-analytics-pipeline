import time
import uuid

import pytest
from utils.clickhouse.poll import poll_for_data
from utils.ingestion.events import create_test_event, send_event


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
    time.sleep(test_config["processing_session_gap_seconds"] + 1)

    # Query for the processed session
    query = """
    SELECT session_id, user_id, start_time, end_time, duration, page_count,
           device_category
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
    Tests that the EventAggregator correctly counts different event types within a
    single window.
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
    time.sleep(test_config["processing_metrics_window_size_seconds"] + 1)

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


def test_performance_tracker_calculates_metrics(clickhouse_client, test_config):
    """
    Tests that the PerformanceTracker correctly calculates load time metrics.
    """
    base_timestamp = int(time.time() * 1000)

    # Create events with different load times
    load_times = [100, 200, 300, 400, 500]  # milliseconds

    for i, load_time in enumerate(load_times):
        event_payload = create_test_event(
            event_type="page_view",
            user_id=f"perf-user-{i}",
            session_id=f"perf-session-{i}",
            load_time=load_time,
        )

        send_event(event_payload, timestamp_override=base_timestamp + i * 1000)

    # Wait for performance window to complete
    time.sleep(test_config["processing_performance_window_size_seconds"] + 1)

    # Query for performance metrics
    query = """
    SELECT device_category, avg_load_time, p95_load_time
    FROM performance_metrics
    WHERE device_category = 'Desktop'
    """

    result = poll_for_data(
        clickhouse_client=clickhouse_client,
        query=query,
        max_wait_time=test_config["max_wait_time"],
        poll_interval=test_config["poll_interval"],
        expected_count=1,
    )

    # Verify performance calculations
    performance_data = result[0]
    device_category = performance_data[0]
    avg_load_time = performance_data[1]
    p95_load_time = performance_data[2]

    assert device_category == "Desktop"
    assert avg_load_time == 300.0  # Average of [100, 200, 300, 400, 500]
    assert p95_load_time >= 400.0  # 95th percentile should be >= 400


@pytest.mark.parametrize(
    "event_type", ["page_view", "click", "conversion", "add_to_cart"]
)
def test_different_event_types_are_processed(
    clickhouse_client, test_config, event_type
):
    """
    Parametrized test to ensure all allowed event types are processed correctly.
    """
    user_id = f"type-user-{uuid.uuid4()}"

    event_payload = create_test_event(event_type=event_type, user_id=user_id)

    send_event(event_payload)

    # Wait for metrics window
    time.sleep(test_config["processing_metrics_window_size_seconds"] + 1)

    # Query for the event in metrics
    query = """
    SELECT event_type, event_count, user_count
    FROM event_metrics
    WHERE event_type = %(event_type)s
    """
    params = {"event_type": event_type}

    result = poll_for_data(
        clickhouse_client=clickhouse_client,
        query=query,
        params=params,
        max_wait_time=test_config["max_wait_time"],
        poll_interval=test_config["poll_interval"],
        expected_count=1,
    )

    # Verify the event was processed
    metrics_data = result[0]
    assert metrics_data[0] == event_type
    assert metrics_data[1] == 1  # event_count
    assert metrics_data[2] == 1  # user_count

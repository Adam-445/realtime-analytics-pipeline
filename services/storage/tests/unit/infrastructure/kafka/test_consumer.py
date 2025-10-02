from unittest.mock import MagicMock, patch

from confluent_kafka import KafkaError
from src.infrastructure.kafka.consumer import KafkaBatchConsumer


def _make_message(topic: str, value: bytes, error=None):
    m = MagicMock()
    m.topic.return_value = topic
    m.value.return_value = value
    m.error.return_value = error
    return m


@patch("src.infrastructure.kafka.consumer.Consumer")
def test_consume_batch_parses_and_groups(mock_consumer_cls):
    mock_consumer = MagicMock()
    mock_consumer_cls.return_value = mock_consumer

    msg1 = _make_message(
        "event_metrics",
        b'{"window_start":"2025-01-01T00:00:00Z","event_type":"click"}',
    )
    msg2 = _make_message(
        "performance_metrics",
        b'{"window_start":"2025-01-01T00:00:00Z","device_category":"desktop"}',
    )
    mock_consumer.consume.return_value = [msg1, msg2]

    c = KafkaBatchConsumer(["event_metrics", "performance_metrics"])
    out = c.consume_batch()

    assert set(out.keys()) == {"event_metrics", "performance_metrics"}
    assert len(out["event_metrics"]) == 1
    assert len(out["performance_metrics"]) == 1


@patch("src.infrastructure.kafka.consumer.Consumer")
def test_consume_batch_ignores_partition_eof(mock_consumer_cls):
    mock_consumer = MagicMock()
    mock_consumer_cls.return_value = mock_consumer

    err = MagicMock()
    err.code.return_value = KafkaError._PARTITION_EOF
    msg_err = _make_message("event_metrics", b"{}", error=err)
    msg_ok = _make_message("event_metrics", b"{}", error=None)
    mock_consumer.consume.return_value = [msg_err, msg_ok]

    c = KafkaBatchConsumer(["event_metrics"])
    out = c.consume_batch()
    assert len(out["event_metrics"]) == 1


@patch("src.infrastructure.kafka.consumer.Consumer")
def test_consume_batch_raises_on_other_error(mock_consumer_cls):
    mock_consumer = MagicMock()
    mock_consumer_cls.return_value = mock_consumer

    err = MagicMock()
    err.code.return_value = 123  # not EOF
    msg_err = _make_message("event_metrics", b"{}", error=err)
    mock_consumer.consume.return_value = [msg_err]

    c = KafkaBatchConsumer(["event_metrics"])
    try:
        c.consume_batch()
        assert False, "Expected exception"
    except Exception:
        pass

from unittest.mock import MagicMock, patch

import pytest
from confluent_kafka import KafkaException
from src.infrastructure.kafka.producer import EventProducer
from src.schemas.analytics_event import (
    AnalyticsEvent,
    ContextInfo,
    DeviceInfo,
    EventInfo,
    EventMetrics,
    UserInfo,
)
from uuid6 import uuid7


def create_test_event(event_id=None):
    """Create a test AnalyticsEvent for testing."""
    return AnalyticsEvent(
        event=EventInfo(id=event_id or uuid7(), type="page_view"),
        user=UserInfo(id="test_user"),
        context=ContextInfo(url="https://example.com", session_id="test_session"),
        device=DeviceInfo(
            user_agent="test_agent", screen_width=1920, screen_height=1080
        ),
        metrics=EventMetrics(load_time=100),
    )


class TestEventProducer:
    """Test Kafka event producer functionality."""

    @patch("src.infrastructure.kafka.producer.settings")
    @patch("src.infrastructure.kafka.producer.Producer")
    def test_producer_initialization(self, mock_producer_class, mock_settings):
        """Test that producer initializes with correct configuration."""
        mock_settings.kafka_bootstrap_servers = "localhost:9092"
        mock_settings.kafka_topic_events = "analytics_events"

        mock_producer = MagicMock()
        mock_producer_class.return_value = mock_producer

        producer = EventProducer()

        # Verify producer was created with correct config
        mock_producer_class.assert_called_once_with(
            {
                "bootstrap.servers": "localhost:9092",
                "message.max.bytes": 10_485_760,
                "acks": "all",
                "batch.size": 1_048_576,
                "linger.ms": 20,
            }
        )

        assert producer.producer == mock_producer
        assert producer.topic == "analytics_events"

    def test_delivery_report_success(self):
        """Test delivery report callback for successful delivery."""
        with patch("src.infrastructure.kafka.producer.logger") as mock_logger:
            producer = EventProducer()

            # Mock successful message
            mock_msg = MagicMock()
            mock_msg.topic.return_value = "test_topic"
            mock_msg.partition.return_value = 0
            mock_msg.offset.return_value = 123

            producer._delivery_report(None, mock_msg)

            mock_logger.debug.assert_called_once_with(
                "kafka_delivery_success",
                extra={"topic": "test_topic", "partition": 0, "offset": 123},
            )

    def test_delivery_report_error(self):
        """Test delivery report callback for failed delivery."""
        with patch("src.infrastructure.kafka.producer.logger") as mock_logger:
            producer = EventProducer()

            error = MagicMock()
            producer._delivery_report(error, None)

            mock_logger.error.assert_called_once_with(
                "kafka_delivery_failed", extra={"error": str(error)}
            )

    @patch("src.infrastructure.kafka.producer.settings")
    @patch("src.infrastructure.kafka.producer.Producer")
    async def test_send_event_success(self, mock_producer_class, mock_settings):
        """Test successful event sending."""
        mock_settings.kafka_bootstrap_servers = "localhost:9092"
        mock_settings.kafka_topic_events = "analytics_events"

        mock_producer = MagicMock()
        mock_producer_class.return_value = mock_producer

        producer = EventProducer()
        event = create_test_event()

        await producer.send_event(event)

        # Verify produce was called with correct parameters
        mock_producer.produce.assert_called_once()
        call_args = mock_producer.produce.call_args

        assert call_args[1]["topic"] == "analytics_events"
        assert call_args[1]["key"] == b"test_user"
        assert isinstance(call_args[1]["value"], bytes)
        assert call_args[1]["callback"] == producer._delivery_report

        # Verify poll was called
        mock_producer.poll.assert_called_once_with(0)

    @patch("src.infrastructure.kafka.producer.settings")
    @patch("src.infrastructure.kafka.producer.Producer")
    async def test_send_event_buffer_error(self, mock_producer_class, mock_settings):
        """Test send_event with buffer full error."""
        mock_settings.kafka_bootstrap_servers = "localhost:9092"
        mock_settings.kafka_topic_events = "analytics_events"

        mock_producer = MagicMock()
        # Simulate buffer full error (Python's built-in BufferError)
        mock_producer.produce.side_effect = BufferError("Queue is full")
        mock_producer_class.return_value = mock_producer

        producer = EventProducer()
        # Mock the flush method
        producer.flush = MagicMock()

        event = create_test_event()

        with pytest.raises(BufferError):
            await producer.send_event(event)

        # Verify flush was called
        producer.flush.assert_called_once()

    @patch("src.infrastructure.kafka.producer.settings")
    @patch("src.infrastructure.kafka.producer.Producer")
    async def test_send_event_kafka_exception(self, mock_producer_class, mock_settings):
        """Test handling of Kafka exception during event sending."""
        mock_settings.kafka_bootstrap_servers = "localhost:9092"
        mock_settings.kafka_topic_events = "analytics_events"

        # Create mock Kafka exception
        mock_error = MagicMock()
        mock_error.code.return_value = "BROKER_NOT_AVAILABLE"
        kafka_exc = KafkaException(mock_error)
        kafka_exc.retriable = MagicMock(return_value=True)

        mock_producer = MagicMock()
        mock_producer.produce.side_effect = kafka_exc
        mock_producer_class.return_value = mock_producer

        with patch("src.infrastructure.kafka.producer.logger") as mock_logger:
            producer = EventProducer()

            test_event_id = uuid7()
            event = create_test_event(event_id=test_event_id)

            with pytest.raises(KafkaException):
                await producer.send_event(event)

            # Verify error was logged with correct details
            mock_logger.error.assert_called_once_with(
                "Kafka produce error",
                extra={
                    "event_id": str(test_event_id),
                    "error_code": "BROKER_NOT_AVAILABLE",
                    "retriable": True,
                },
            )

    @patch("src.infrastructure.kafka.producer.settings")
    @patch("src.infrastructure.kafka.producer.Producer")
    async def test_send_event_unexpected_exception(
        self, mock_producer_class, mock_settings
    ):
        """Test handling of unexpected exception during event sending."""
        mock_settings.kafka_bootstrap_servers = "localhost:9092"
        mock_settings.kafka_topic_events = "analytics_events"

        mock_producer = MagicMock()
        mock_producer.produce.side_effect = RuntimeError("Unexpected error")
        mock_producer_class.return_value = mock_producer

        with patch("src.infrastructure.kafka.producer.logger") as mock_logger:
            producer = EventProducer()
            event = create_test_event()

            with pytest.raises(RuntimeError):
                await producer.send_event(event)

            # Verify exception was logged
            mock_logger.exception.assert_called_once_with(
                "producer_unexpected_error", extra={"error": "Unexpected error"}
            )

    @patch("src.infrastructure.kafka.producer.settings")
    @patch("src.infrastructure.kafka.producer.Producer")
    def test_flush_success(self, mock_producer_class, mock_settings):
        """Test successful message flush."""
        mock_settings.kafka_bootstrap_servers = "localhost:9092"
        mock_settings.kafka_topic_events = "analytics_events"

        mock_producer = MagicMock()
        mock_producer.flush.return_value = 0  # All messages delivered
        mock_producer_class.return_value = mock_producer

        producer = EventProducer()
        producer.flush()

        mock_producer.flush.assert_called_once_with(timeout=5)

    @patch("src.infrastructure.kafka.producer.settings")
    @patch("src.infrastructure.kafka.producer.Producer")
    def test_flush_with_remaining_messages(self, mock_producer_class, mock_settings):
        """Test flush when some messages remain undelivered."""
        mock_settings.kafka_bootstrap_servers = "localhost:9092"
        mock_settings.kafka_topic_events = "analytics_events"

        mock_producer = MagicMock()
        mock_producer.flush.return_value = 3  # 3 messages not delivered
        mock_producer_class.return_value = mock_producer

        with patch("src.infrastructure.kafka.producer.logger") as mock_logger:
            producer = EventProducer()
            producer.flush()

            mock_producer.flush.assert_called_once_with(timeout=5)
            mock_logger.warning.assert_called_once_with(
                "producer_flush_remaining", extra={"remaining_messages": 3}
            )

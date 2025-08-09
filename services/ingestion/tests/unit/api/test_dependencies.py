from unittest.mock import patch

from src.api.v1.dependencies import get_kafka_producer
from src.core.config import Settings, settings
from src.infrastructure.kafka.producer import EventProducer


class TestSettings:
    """Test cases for Settings configuration."""

    def test_default_settings(self):
        """Test default configuration values."""
        # Create settings without any environment variables
        import os

        original_env = os.environ.get("APP_ENVIRONMENT")
        if "APP_ENVIRONMENT" in os.environ:
            del os.environ["APP_ENVIRONMENT"]

        try:
            default_settings = Settings()

            assert default_settings.kafka_bootstrap_servers == "kafka1:19092"
            assert default_settings.kafka_topic_events == "analytics_events"
            assert default_settings.kafka_topic_event_metrics == "event_metrics"
            assert default_settings.kafka_topic_session_metrics == "session_metrics"
            assert (
                default_settings.kafka_topic_performance_metrics
                == "performance_metrics"
            )
            assert default_settings.otel_service_name == "ingestion"
            assert default_settings.app_environment == "production"
        finally:
            if original_env is not None:
                os.environ["APP_ENVIRONMENT"] = original_env
        assert default_settings.app_log_level == "INFO"

    def test_kafka_consumer_topics_list(self):
        """Test that consumer topics list contains expected topics."""
        assert "event_metrics" in settings.kafka_consumer_topics
        assert "session_metrics" in settings.kafka_consumer_topics
        assert "performance_metrics" in settings.kafka_consumer_topics

    def test_log_redaction_patterns(self):
        """Test log redaction patterns for security."""
        expected_patterns = [
            "password",
            "token",
            "secret",
            "key",
            "authorization",
            "cookie",
            "session",
        ]

        for pattern in expected_patterns:
            assert pattern in settings.app_log_redaction_patterns

    def test_settings_with_environment_variables(self):
        """Test settings override with environment variables."""
        with patch.dict(
            "os.environ",
            {
                "KAFKA_BOOTSTRAP_SERVERS": "localhost:9092",
                "APP_LOG_LEVEL": "DEBUG",
                "APP_ENVIRONMENT": "development",
            },
        ):
            test_settings = Settings()

            assert test_settings.kafka_bootstrap_servers == "localhost:9092"
            assert test_settings.app_log_level == "DEBUG"
            assert test_settings.app_environment == "development"

    def test_settings_types(self):
        """Test that settings have correct types."""
        assert isinstance(settings.kafka_bootstrap_servers, str)
        assert isinstance(settings.kafka_consumer_topics, list)
        assert isinstance(settings.app_log_redaction_patterns, list)
        assert isinstance(settings.kafka_topic_events, str)


class TestDependencies:
    """Test cases for dependency injection."""

    def test_get_kafka_producer_singleton(self):
        """Test that get_kafka_producer returns the same instance."""
        # Clear any existing cache
        get_kafka_producer.cache_clear()

        producer1 = get_kafka_producer()
        producer2 = get_kafka_producer()

        assert producer1 is producer2
        assert isinstance(producer1, EventProducer)

    def test_get_kafka_producer_type(self):
        """Test that get_kafka_producer returns correct type."""
        producer = get_kafka_producer()
        assert isinstance(producer, EventProducer)

    def test_get_kafka_producer_cache_info(self):
        """Test that caching is working correctly."""
        # Clear cache first
        get_kafka_producer.cache_clear()
        cache_info = get_kafka_producer.cache_info()
        assert cache_info.hits == 0
        assert cache_info.misses == 0

        # First call should be a miss
        get_kafka_producer()
        cache_info = get_kafka_producer.cache_info()
        assert cache_info.misses == 1
        assert cache_info.hits == 0

        # Second call should be a hit
        get_kafka_producer()
        cache_info = get_kafka_producer.cache_info()
        assert cache_info.hits == 1
        assert cache_info.misses == 1

    def test_get_kafka_producer_cache_clear(self):
        """Test that cache can be cleared."""
        # Get producer first
        get_kafka_producer()

        # Clear cache
        get_kafka_producer.cache_clear()

        # Get producer again
        get_kafka_producer()

        # Cache should have been cleared and refilled
        cache_info = get_kafka_producer.cache_info()
        assert cache_info.misses >= 1

    @patch("src.infrastructure.kafka.producer.Producer")
    def test_producer_initialization_with_mocked_kafka(self, mock_producer_class):
        """Test producer initialization with mocked Kafka client."""
        # Clear cache to ensure fresh initialization
        get_kafka_producer.cache_clear()

        get_kafka_producer()

        # Verify that the Kafka Producer was initialized
        mock_producer_class.assert_called_once()

        # Verify configuration passed to Kafka Producer
        call_args = mock_producer_class.call_args[0][0]
        assert "bootstrap.servers" in call_args
        assert "acks" in call_args
        assert "batch.size" in call_args
        assert "linger.ms" in call_args

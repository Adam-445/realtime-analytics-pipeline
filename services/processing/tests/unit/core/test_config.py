from src.core.config import Settings, settings


class TestSettings:
    """Test Settings configuration class."""

    def test_default_values(self):
        """Test that default values are set correctly."""
        config = Settings()

        # Kafka settings
        assert config.kafka_bootstrap_servers == "kafka1:19092"
        assert config.kafka_topic_events == "analytics_events"
        assert config.kafka_topic_event_metrics == "event_metrics"
        assert config.kafka_topic_session_metrics == "session_metrics"
        assert config.kafka_topic_performance_metrics == "performance_metrics"
        assert config.processing_kafka_consumer_group == "flink-analytics-group"
        assert config.processing_kafka_scan_startup_mode == "earliest-offset"

        # Flink settings
        assert config.flink_parallelism == 2
        assert config.flink_checkpoint_interval_ms == 30000
        assert config.flink_watermark_delay_seconds == 10
        assert config.flink_idle_timeout_seconds == 5
        assert config.processing_metrics_window_size_seconds == 60
        assert config.processing_performance_window_size_seconds == 300
        assert config.processing_session_gap_seconds == 1800

        # Event filtering
        assert config.processing_allowed_event_types == [
            "page_view",
            "click",
            "conversion",
            "add_to_cart",
        ]

        # Logging and environment
        assert config.app_log_level == "INFO"
        assert "password" in config.app_log_redaction_patterns
        assert "token" in config.app_log_redaction_patterns
        assert config.otel_service_name == "processing"
        # Note: app_environment might be overridden in test environments
        assert config.app_environment in ["production", "testing"]

    def test_custom_values(self):
        """Test that custom values can be set."""
        config = Settings(
            kafka_bootstrap_servers="localhost:9092",
            flink_parallelism=4,
            app_log_level="DEBUG",
        )

        assert config.kafka_bootstrap_servers == "localhost:9092"
        assert config.flink_parallelism == 4
        assert config.app_log_level == "DEBUG"

    def test_allowed_event_types_validation(self):
        """Test that allowed event types are properly configured."""
        config = Settings()

        # Test that all expected event types are present
        expected_types = ["page_view", "click", "conversion", "add_to_cart"]
        for event_type in expected_types:
            assert event_type in config.processing_allowed_event_types

    def test_redaction_patterns(self):
        """Test that sensitive data patterns are configured."""
        config = Settings()

        sensitive_patterns = [
            "password",
            "token",
            "secret",
            "key",
            "authorization",
            "cookie",
            "session",
        ]

        for pattern in sensitive_patterns:
            assert pattern in config.app_log_redaction_patterns

    def test_flink_configuration_sanity(self):
        """Test that Flink configuration values are sensible."""
        config = Settings()

        # Test that parallelism is positive
        assert config.flink_parallelism > 0

        # Test that checkpoint interval is reasonable (not too frequent)
        assert config.flink_checkpoint_interval_ms >= 1000  # At least 1 second

        # Test that watermark delay is reasonable
        assert config.flink_watermark_delay_seconds > 0
        assert config.flink_watermark_delay_seconds < 300  # Less than 5 minutes

        # Test that window sizes are reasonable
        assert config.processing_metrics_window_size_seconds > 0
        assert config.processing_performance_window_size_seconds > 0
        assert config.processing_session_gap_seconds > 0

    def test_settings_singleton(self):
        """Test that the settings singleton is properly configured."""
        # Test that the global settings object exists
        assert settings is not None
        assert isinstance(settings, Settings)

        # Test that it has the expected attributes
        assert hasattr(settings, "kafka_bootstrap_servers")
        assert hasattr(settings, "flink_parallelism")
        assert hasattr(settings, "otel_service_name")

from src.core.config import Settings, settings


class TestSettings:
    """Test configuration settings."""

    def test_default_values(self):
        """Test that default values are set correctly."""
        config = Settings()

        assert config.kafka_bootstrap_servers == "kafka1:19092"
        assert config.kafka_topic_events == "analytics_events"
        assert config.kafka_topic_event_metrics == "event_metrics"
        assert config.kafka_topic_session_metrics == "session_metrics"
        assert config.kafka_topic_performance_metrics == "performance_metrics"
        assert config.kafka_consumer_topics == [
            "event_metrics",
            "session_metrics",
            "performance_metrics",
        ]
        assert config.otel_service_name == "ingestion"
        # Note: app_environment might be overridden in test environments
        assert config.app_environment in ["production", "testing"]
        assert config.app_log_level == "INFO"
        assert config.app_log_redaction_patterns == [
            "password",
            "token",
            "secret",
            "key",
            "authorization",
            "cookie",
            "session",
        ]

    def test_settings_singleton(self):
        """Test that settings is a proper singleton instance."""
        assert isinstance(settings, Settings)
        assert settings.kafka_bootstrap_servers == "kafka1:19092"

    def test_custom_kafka_servers(self):
        """Test custom Kafka bootstrap servers."""
        config = Settings(kafka_bootstrap_servers="localhost:9092")
        assert config.kafka_bootstrap_servers == "localhost:9092"

    def test_custom_topics(self):
        """Test custom topic configuration."""
        config = Settings(
            kafka_topic_events="custom_events",
            kafka_topic_event_metrics="custom_event_metrics",
        )
        assert config.kafka_topic_events == "custom_events"
        assert config.kafka_topic_event_metrics == "custom_event_metrics"

    def test_custom_environment(self):
        """Test custom environment configuration."""
        config = Settings(app_environment="development", app_log_level="DEBUG")
        assert config.app_environment == "development"
        assert config.app_log_level == "DEBUG"

    def test_custom_consumer_topics(self):
        """Test custom consumer topics list."""
        custom_topics = ["topic1", "topic2"]
        config = Settings(kafka_consumer_topics=custom_topics)
        assert config.kafka_consumer_topics == custom_topics

    def test_custom_redaction_patterns(self):
        """Test custom log redaction patterns."""
        custom_patterns = ["custom_secret", "api_key"]
        config = Settings(app_log_redaction_patterns=custom_patterns)
        assert config.app_log_redaction_patterns == custom_patterns

    def test_otel_service_name(self):
        """Test OpenTelemetry service name configuration."""
        config = Settings(otel_service_name="test_service")
        assert config.otel_service_name == "test_service"

from unittest.mock import patch

import pytest
from src.startup import initialize_application


class TestApplicationStartup:
    """Test cases for application initialization."""

    @patch("src.startup.create_topics")
    @patch("src.startup.configure_logging")
    @patch("src.startup.logger")  # Patch the module-level logger
    def test_initialize_application_success(
        self, mock_logger, mock_configure_logging, mock_create_topics
    ):
        """Test successful application initialization."""
        initialize_application()

        # Verify logging configuration
        mock_configure_logging.assert_called_once()

        # Verify topic creation
        mock_create_topics.assert_called_once()

        # Verify logging calls
        assert mock_logger.info.call_count == 2

        # Check log messages match structured message names
        log_calls = [call.args[0] for call in mock_logger.info.call_args_list]
        assert "initializing_application" in log_calls
        assert "application_initialized" in log_calls

    @patch("src.startup.create_topics")
    @patch("src.startup.configure_logging")
    @patch("src.startup.logger")  # Patch the module-level logger
    @patch("src.startup.settings")
    def test_initialize_application_with_settings_logging(
        self, mock_settings, mock_logger, mock_configure_logging, mock_create_topics
    ):
        """Test initialization includes settings in completion log."""
        mock_settings.kafka_consumer_topics = ["topic1", "topic2"]
        mock_settings.otel_service_name = "test-service"

        initialize_application()

        # Verify the completion log includes extra data
        completion_call = mock_logger.info.call_args_list[-1]
        assert "application_initialized" in completion_call.args[0]
        assert "extra" in completion_call.kwargs

        extra_data = completion_call.kwargs["extra"]
        assert "kafka_topics" in extra_data
        assert "otel_service" in extra_data
        assert extra_data["kafka_topics"] == ["topic1", "topic2"]
        assert extra_data["otel_service"] == "test-service"

    @patch("src.startup.create_topics")
    @patch("src.startup.configure_logging")
    @patch("src.startup.logger")  # Patch the module-level logger
    def test_initialize_application_create_topics_error(
        self, mock_logger, mock_configure_logging, mock_create_topics
    ):
        """Test initialization handles topic creation errors."""
        mock_create_topics.side_effect = Exception("Kafka unavailable")

        with pytest.raises(Exception, match="Kafka unavailable"):
            initialize_application()

        # Verify logging was configured before the error
        mock_configure_logging.assert_called_once()

        # Verify startup logging occurred before error
        startup_calls = [
            call
            for call in mock_logger.info.call_args_list
            if "initializing_application" in call.args[0]
        ]
        assert len(startup_calls) == 1

    @patch("src.startup.create_topics")
    @patch("src.startup.configure_logging")
    @patch("src.startup.logger")  # Patch the module-level logger
    def test_initialize_application_logging_error(
        self, mock_logger, mock_configure_logging, mock_create_topics
    ):
        """Test initialization handles logging configuration errors."""
        mock_configure_logging.side_effect = Exception("Logging setup failed")

        with pytest.raises(Exception, match="Logging setup failed"):
            initialize_application()

        # Topics should not be created if logging fails
        mock_create_topics.assert_not_called()

    @patch("src.startup.create_topics")
    @patch("src.startup.configure_logging")
    @patch("src.startup.logger")  # Patch the module-level logger
    def test_initialize_application_call_order(
        self, mock_logger, mock_configure_logging, mock_create_topics
    ):
        """Test that initialization steps happen in correct order."""
        call_order = []

        def track_configure_logging(**kwargs):
            call_order.append("configure_logging")

        def track_create_topics():
            call_order.append("create_topics")

        mock_configure_logging.side_effect = track_configure_logging
        mock_create_topics.side_effect = track_create_topics

        initialize_application()

        # Verify correct order: logging first, then topics
        assert call_order == ["configure_logging", "create_topics"]

    @patch("src.startup.create_topics")
    @patch("src.startup.configure_logging")
    @patch("src.startup.logger")  # Patch the module-level logger
    def test_initialize_application_logger_name(
        self, mock_logger, mock_configure_logging, mock_create_topics
    ):
        """Test that logger is used properly."""
        initialize_application()

        # Verify logger info was called (module-level logger is patched)
        assert mock_logger.info.called

import json
import logging
from datetime import datetime
from unittest.mock import MagicMock, patch

from src.core.logging_config import (
    CustomJsonFormatter,
    SensitiveDataFilter,
    configure_logging,
)


class TestSensitiveDataFilter:
    """Test sensitive data filtering functionality."""

    def test_filter_removes_sensitive_data(self):
        """Test that sensitive data is redacted based on patterns."""
        with patch("src.core.logging_config.settings") as mock_settings:
            mock_settings.app_log_redaction_patterns = ["password", "token", "secret"]

            data = {
                "username": "john_doe",
                "password": "secret123",
                "api_token": "abc123",
                "user_secret": "hidden",
                "regular_field": "visible",
            }

            filtered = SensitiveDataFilter.filter(data)

            assert filtered["username"] == "john_doe"
            assert filtered["password"] == "[REDACTED]"
            assert filtered["api_token"] == "[REDACTED]"
            assert filtered["user_secret"] == "[REDACTED]"
            assert filtered["regular_field"] == "visible"

    def test_filter_handles_nested_objects(self):
        """Test that filtering works recursively on nested dictionaries."""
        with patch("src.core.logging_config.settings") as mock_settings:
            mock_settings.app_log_redaction_patterns = ["password"]

            data = {
                "user": {
                    "name": "john",
                    "password": "secret123",
                    "profile": {
                        "password_hint": "pet name",
                        "age": 30,
                    },
                },
                "regular": "data",
            }

            filtered = SensitiveDataFilter.filter(data)

            assert filtered["user"]["name"] == "john"
            assert filtered["user"]["password"] == "[REDACTED]"
            assert filtered["user"]["profile"]["password_hint"] == "[REDACTED]"
            assert filtered["user"]["profile"]["age"] == 30
            assert filtered["regular"] == "data"

    def test_filter_with_empty_patterns(self):
        """Test that filter works when no patterns are configured."""
        with patch("src.core.logging_config.settings") as mock_settings:
            mock_settings.app_log_redaction_patterns = []

            data = {"password": "secret", "token": "abc123"}
            filtered = SensitiveDataFilter.filter(data)

            assert filtered == data

    def test_filter_preserves_non_dict_values(self):
        """Test that non-dict values are preserved correctly."""
        with patch("src.core.logging_config.settings") as mock_settings:
            mock_settings.app_log_redaction_patterns = ["password"]

            data = {
                "password": "secret",
                "number": 42,
                "list": [1, 2, 3],
                "none_value": None,
            }

            filtered = SensitiveDataFilter.filter(data)

            assert filtered["password"] == "[REDACTED]"
            assert filtered["number"] == 42
            assert filtered["list"] == [1, 2, 3]
            assert filtered["none_value"] is None


class TestCustomJsonFormatter:
    """Test custom JSON formatter functionality."""

    @patch("src.core.logging_config.settings")
    @patch("socket.gethostname")
    @patch("os.getpid")
    def test_formatter_initialization(
        self, mock_getpid, mock_gethostname, mock_settings
    ):
        """Test that formatter initializes with correct values."""
        mock_gethostname.return_value = "test-host"
        mock_getpid.return_value = 12345
        mock_settings.otel_service_name = "test-service"
        mock_settings.app_environment = "test"

        formatter = CustomJsonFormatter()

        assert formatter.hostname == "test-host"
        assert formatter.pid == 12345
        assert formatter.service_name == "test-service"
        assert formatter.environment == "test"
        assert formatter.sensitive_filter is not None

    @patch("src.core.logging_config.settings")
    @patch("socket.gethostname", return_value="test-host")
    @patch("os.getpid", return_value=12345)
    def test_format_basic_record(self, mock_getpid, mock_gethostname, mock_settings):
        """Test formatting of a basic log record."""
        mock_settings.otel_service_name = "test-service"
        mock_settings.app_environment = "test"
        mock_settings.app_log_redaction_patterns = []

        formatter = CustomJsonFormatter()

        # Create a mock log record
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="/test/path.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        formatted = formatter.format(record)
        parsed = json.loads(formatted)

        assert parsed["service"] == "test-service"
        assert parsed["hostname"] == "test-host"
        assert parsed["pid"] == 12345
        assert parsed["environment"] == "test"
        assert parsed["name"] == "test.logger"
        assert parsed["levelname"] == "INFO"
        assert parsed["msg"] == "Test message"
        assert "timestamp" in parsed

        # Verify timestamp format
        datetime.fromisoformat(parsed["timestamp"].replace("Z", "+00:00"))

    @patch("src.core.logging_config.settings")
    @patch("socket.gethostname", return_value="test-host")
    @patch("os.getpid", return_value=12345)
    def test_format_record_with_exception(
        self, mock_getpid, mock_gethostname, mock_settings
    ):
        """Test formatting of a log record with exception information."""
        mock_settings.otel_service_name = "test-service"
        mock_settings.app_environment = "test"
        mock_settings.app_log_redaction_patterns = []

        formatter = CustomJsonFormatter()

        try:
            raise ValueError("Test exception")
        except ValueError:
            import sys

            exc_info = sys.exc_info()

            record = logging.LogRecord(
                name="test.logger",
                level=logging.ERROR,
                pathname="/test/path.py",
                lineno=42,
                msg="Error occurred",
                args=(),
                exc_info=exc_info,
            )

            formatted = formatter.format(record)
            parsed = json.loads(formatted)

            assert "exception" in parsed
            assert parsed["exception"]["type"] == "ValueError"
            assert parsed["exception"]["message"] == "Test exception"
            assert isinstance(parsed["exception"]["stack"], list)

    @patch("src.core.logging_config.settings")
    @patch("socket.gethostname", return_value="test-host")
    @patch("os.getpid", return_value=12345)
    def test_format_applies_sensitive_filter(
        self, mock_getpid, mock_gethostname, mock_settings
    ):
        """Test that sensitive data filtering is applied during formatting."""
        mock_settings.otel_service_name = "test-service"
        mock_settings.app_environment = "test"
        mock_settings.app_log_redaction_patterns = ["password"]

        formatter = CustomJsonFormatter()

        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="/test/path.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        # Add a sensitive field to the record
        record.password = "secret123"

        formatted = formatter.format(record)
        parsed = json.loads(formatted)

        assert parsed["password"] == "[REDACTED]"

    def test_format_exception_method(self):
        """Test the format_exception method specifically."""
        formatter = CustomJsonFormatter()

        try:
            raise RuntimeError("Test runtime error")
        except RuntimeError:
            import sys

            exc_info = sys.exc_info()

            formatted_exc = formatter.format_exception(exc_info)

            assert formatted_exc["type"] == "RuntimeError"
            assert formatted_exc["message"] == "Test runtime error"
            assert isinstance(formatted_exc["stack"], list)
            assert len(formatted_exc["stack"]) > 0


class TestConfigureLogging:
    """Test logging configuration function."""

    @patch("src.core.logging_config.settings")
    def test_configure_logging_basic(self, mock_settings):
        """Test basic logging configuration."""
        mock_settings.otel_service_name = "test-service"
        mock_settings.app_environment = "test"
        mock_settings.app_log_level = "INFO"
        mock_settings.app_log_redaction_patterns = []

        with patch("logging.getLogger") as mock_get_logger:
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger

            result = configure_logging()

            assert result == mock_logger
            assert mock_logger.setLevel.called
            assert len(mock_logger.handlers) == 1

    @patch("src.core.logging_config.settings")
    def test_configure_logging_different_levels(self, mock_settings):
        """Test logging configuration with different log levels."""
        mock_settings.otel_service_name = "test-service"
        mock_settings.app_environment = "test"
        mock_settings.app_log_redaction_patterns = []

        test_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

        for level in test_levels:
            mock_settings.app_log_level = level

            with patch("logging.getLogger") as mock_get_logger:
                mock_logger = MagicMock()
                mock_get_logger.return_value = mock_logger

                configure_logging()

                expected_level = getattr(logging, level)
                mock_logger.setLevel.assert_called_with(expected_level)

    @patch("src.core.logging_config.settings")
    def test_configure_logging_invalid_level(self, mock_settings):
        """Test logging configuration with invalid log level falls back to INFO."""
        mock_settings.otel_service_name = "test-service"
        mock_settings.app_environment = "test"
        mock_settings.app_log_level = "INVALID"
        mock_settings.app_log_redaction_patterns = []

        with patch("logging.getLogger") as mock_get_logger:
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger

            configure_logging()

            # Should fall back to INFO level
            mock_logger.setLevel.assert_called_with(logging.INFO)

    @patch("src.core.logging_config.settings")
    def test_configure_logging_handler_setup(self, mock_settings):
        """Test that console handler is properly configured."""
        mock_settings.otel_service_name = "test-service"
        mock_settings.app_environment = "test"
        mock_settings.app_log_level = "INFO"
        mock_settings.app_log_redaction_patterns = []

        with patch("logging.getLogger") as mock_get_logger, patch(
            "logging.StreamHandler"
        ) as mock_stream_handler:

            mock_logger = MagicMock()
            mock_handler = MagicMock()
            mock_get_logger.return_value = mock_logger
            mock_stream_handler.return_value = mock_handler

            configure_logging()

            # Verify handler setup
            mock_stream_handler.assert_called_once()
            mock_handler.setFormatter.assert_called_once()

            # Verify formatter is CustomJsonFormatter
            formatter_call = mock_handler.setFormatter.call_args[0][0]
            assert isinstance(formatter_call, CustomJsonFormatter)

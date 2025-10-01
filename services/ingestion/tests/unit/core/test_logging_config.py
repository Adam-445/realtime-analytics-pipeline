import json
import logging
from datetime import datetime
from unittest.mock import MagicMock, patch

from shared.logging.json import (
    CustomJsonFormatter,
    SensitiveDataFilter,
    configure_logging,
)


class TestSensitiveDataFilter:
    """Test sensitive data filtering functionality."""

    def test_filter_removes_sensitive_data(self):
        """Test that sensitive data is redacted based on patterns."""
        sdf = SensitiveDataFilter(["password", "token", "secret"])

        data = {
            "username": "john_doe",
            "password": "secret123",
            "api_token": "abc123",
            "user_secret": "hidden",
            "regular_field": "visible",
        }

        filtered = sdf.filter(data)

        assert filtered["username"] == "john_doe"
        assert filtered["password"] == "[REDACTED]"
        assert filtered["api_token"] == "[REDACTED]"
        assert filtered["user_secret"] == "[REDACTED]"
        assert filtered["regular_field"] == "visible"

    def test_filter_handles_nested_objects(self):
        """Test that filtering works recursively on nested dictionaries."""
        sdf = SensitiveDataFilter(["password"])

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

        filtered = sdf.filter(data)

        assert filtered["user"]["name"] == "john"
        assert filtered["user"]["password"] == "[REDACTED]"
        assert filtered["user"]["profile"]["password_hint"] == "[REDACTED]"
        assert filtered["user"]["profile"]["age"] == 30
        assert filtered["regular"] == "data"

    def test_filter_with_empty_patterns(self):
        """Test that filter works when no patterns are configured."""
        sdf = SensitiveDataFilter([])

        data = {"password": "secret", "token": "abc123"}
        filtered = sdf.filter(data)

        assert filtered == data

    def test_filter_preserves_non_dict_values(self):
        """Test that non-dict values are preserved correctly."""
        sdf = SensitiveDataFilter(["password"])

        data = {
            "password": "secret",
            "number": 42,
            "list": [1, 2, 3],
            "none_value": None,
        }

        filtered = sdf.filter(data)

        assert filtered["password"] == "[REDACTED]"
        assert filtered["number"] == 42
        assert filtered["list"] == [1, 2, 3]
        assert filtered["none_value"] is None


class TestCustomJsonFormatter:
    """Test custom JSON formatter functionality."""

    @patch("socket.gethostname")
    @patch("os.getpid")
    def test_formatter_initialization(self, mock_getpid, mock_gethostname):
        """Test that formatter initializes with correct values."""
        mock_gethostname.return_value = "test-host"
        mock_getpid.return_value = 12345

        formatter = CustomJsonFormatter(
            service="test-service",
            environment="test",
            redaction_patterns=[],
        )

        assert formatter.hostname == "test-host"
        assert formatter.pid == 12345
        assert formatter.service_name == "test-service"
        assert formatter.environment == "test"
        assert formatter.sensitive_filter is not None

    @patch("socket.gethostname", return_value="test-host")
    @patch("os.getpid", return_value=12345)
    def test_format_basic_record(self, mock_getpid, mock_gethostname):
        """Test formatting of a basic log record."""
        formatter = CustomJsonFormatter(
            service="test-service",
            environment="test",
            redaction_patterns=[],
        )

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

    @patch("socket.gethostname", return_value="test-host")
    @patch("os.getpid", return_value=12345)
    def test_format_record_with_exception(self, mock_getpid, mock_gethostname):
        """Test formatting of a log record with exception information."""
        formatter = CustomJsonFormatter(
            service="test-service",
            environment="test",
            redaction_patterns=[],
        )

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

    @patch("socket.gethostname", return_value="test-host")
    @patch("os.getpid", return_value=12345)
    def test_format_applies_sensitive_filter(self, mock_getpid, mock_gethostname):
        """Test that sensitive data filtering is applied during formatting."""
        formatter = CustomJsonFormatter(
            service="test-service",
            environment="test",
            redaction_patterns=["password"],
        )

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
        formatter = CustomJsonFormatter(
            service="svc",
            environment="env",
            redaction_patterns=[],
        )

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

    def test_configure_logging_basic(self):
        """Test basic logging configuration."""
        with patch("logging.getLogger") as mock_get_logger:
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger

            result = configure_logging(
                service="test-service",
                environment="test",
                level="INFO",
                redaction_patterns=[],
            )

            assert result == mock_logger
            assert mock_logger.setLevel.called
            assert len(mock_logger.handlers) == 1

    def test_configure_logging_different_levels(self):
        """Test logging configuration with different log levels."""
        test_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

        for level in test_levels:
            with patch("logging.getLogger") as mock_get_logger:
                mock_logger = MagicMock()
                mock_get_logger.return_value = mock_logger

                configure_logging(
                    service="test-service",
                    environment="test",
                    level=level,
                    redaction_patterns=[],
                )

                expected_level = getattr(logging, level)
                mock_logger.setLevel.assert_called_with(expected_level)

    def test_configure_logging_invalid_level(self):
        """Test logging configuration with invalid log level falls back to INFO."""
        with patch("logging.getLogger") as mock_get_logger:
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger

            configure_logging(
                service="test-service",
                environment="test",
                level="INVALID",
                redaction_patterns=[],
            )

            # Should fall back to INFO level
            mock_logger.setLevel.assert_called_with(logging.INFO)

    def test_configure_logging_handler_setup(self):
        """Test that console handler is properly configured."""
        with patch("logging.getLogger") as mock_get_logger, patch(
            "logging.StreamHandler"
        ) as mock_stream_handler:

            mock_logger = MagicMock()
            mock_handler = MagicMock()
            mock_get_logger.return_value = mock_logger
            mock_stream_handler.return_value = mock_handler

            configure_logging(
                service="test-service",
                environment="test",
                level="INFO",
                redaction_patterns=[],
            )

            # Verify handler setup
            mock_stream_handler.assert_called_once()
            mock_handler.setFormatter.assert_called_once()

            # Verify formatter is CustomJsonFormatter
            formatter_call = mock_handler.setFormatter.call_args[0][0]
            assert isinstance(formatter_call, CustomJsonFormatter)

import logging
from unittest.mock import patch

from src.core.logger import get_logger


class TestLogger:
    """Test logger functionality."""

    def test_get_logger_returns_logger(self):
        """Test that get_logger returns a proper Logger instance."""
        logger = get_logger("test_logger")

        assert isinstance(logger, logging.Logger)
        assert logger.name == "test_logger"

    def test_get_logger_propagation_enabled(self):
        """Test that logger propagation is enabled."""
        logger = get_logger("test_propagation")

        assert logger.propagate is True

    def test_get_logger_same_name_returns_same_instance(self):
        """Test that calling get_logger with same name returns same instance."""
        logger1 = get_logger("same_name")
        logger2 = get_logger("same_name")

        assert logger1 is logger2

    def test_get_logger_different_names_return_different_instances(self):
        """Test that different names return different logger instances."""
        logger1 = get_logger("logger_one")
        logger2 = get_logger("logger_two")

        assert logger1 is not logger2
        assert logger1.name == "logger_one"
        assert logger2.name == "logger_two"

    @patch("logging.getLogger")
    def test_get_logger_calls_logging_getLogger(self, mock_get_logger):
        """Test that get_logger calls logging.getLogger with correct name."""
        mock_logger = logging.Logger("test")
        mock_get_logger.return_value = mock_logger

        result = get_logger("test_name")

        mock_get_logger.assert_called_once_with("test_name")
        assert result.propagate is True

    def test_get_logger_with_empty_string(self):
        """Test get_logger with empty string name."""
        logger = get_logger("")

        assert isinstance(logger, logging.Logger)
        # Empty string becomes root logger
        assert logger.name == "root"
        assert logger.propagate is True

    def test_get_logger_with_dotted_name(self):
        """Test get_logger with hierarchical dotted name."""
        logger = get_logger("module.submodule.component")

        assert isinstance(logger, logging.Logger)
        assert logger.name == "module.submodule.component"
        assert logger.propagate is True

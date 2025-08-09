import logging
from unittest.mock import MagicMock, patch

import pytest
from src.jobs.base_job import BaseJob


class ConcreteJob(BaseJob):
    """Concrete implementation of BaseJob for testing."""

    def build_pipeline(self, t_env):
        """Test implementation of build_pipeline."""
        # Return None to match the abstract method signature
        return None


class TestBaseJob:
    """Test BaseJob abstract class."""

    def test_base_job_initialization(self):
        """Test that BaseJob initializes correctly."""
        job = ConcreteJob("test_job", "test_sink")

        assert job.name == "test_job"
        assert job.sink_name == "test_sink"
        assert isinstance(job.logger, logging.Logger)

    @patch("src.jobs.base_job.get_logger")
    def test_base_job_logger_creation(self, mock_get_logger):
        """Test that BaseJob creates logger with correct name."""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        job = ConcreteJob("test_job", "test_sink")

        mock_get_logger.assert_called_once_with("test_job")
        assert job.logger == mock_logger

    def test_base_job_cannot_be_instantiated_directly(self):
        """Test that BaseJob cannot be instantiated directly."""
        with pytest.raises(TypeError):
            BaseJob("test", "test")  # type: ignore

    def test_concrete_job_has_build_pipeline_method(self):
        """Test that concrete implementation has build_pipeline method."""
        job = ConcreteJob("test_job", "test_sink")

        assert hasattr(job, "build_pipeline")
        assert callable(job.build_pipeline)

    def test_build_pipeline_is_called_correctly(self):
        """Test that build_pipeline can be called with t_env."""
        job = ConcreteJob("test_job", "test_sink")
        mock_t_env = MagicMock()

        result = job.build_pipeline(mock_t_env)

        # Our concrete implementation returns None, which is valid
        assert result is None

    def test_job_attributes_are_strings(self):
        """Test that job name and sink_name are stored as strings."""
        job = ConcreteJob("job_name", "sink_name")

        assert isinstance(job.name, str)
        assert isinstance(job.sink_name, str)

    def test_job_with_empty_names(self):
        """Test job creation with empty strings."""
        job = ConcreteJob("", "")

        assert job.name == ""
        assert job.sink_name == ""
        assert isinstance(job.logger, logging.Logger)


class IncompleteJob(BaseJob):
    """Job missing build_pipeline implementation for testing."""

    pass


class TestAbstractMethods:
    """Test abstract method enforcement."""

    def test_incomplete_job_cannot_be_instantiated(self):
        """Test that job without build_pipeline cannot be instantiated."""
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            IncompleteJob("test", "test")  # type: ignore

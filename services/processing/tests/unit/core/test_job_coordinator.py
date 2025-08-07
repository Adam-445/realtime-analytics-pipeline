from unittest.mock import MagicMock, patch

from src.core.job_coordinator import JobCoordinator


class TestJobCoordinator:
    """Test job coordination and execution functionality."""

    @patch("src.core.job_coordinator.StreamExecutionEnvironment")
    @patch("src.core.job_coordinator.StreamTableEnvironment")
    @patch("src.core.job_coordinator.settings")
    def test_init_creates_execution_environments(
        self, mock_settings, mock_table_env, mock_stream_env
    ):
        """Test that JobCoordinator initializes execution environments."""
        mock_settings.flink_parallelism = 4
        mock_settings.flink_checkpoint_interval_ms = 10000
        mock_settings.flink_idle_timeout_seconds = 30

        mock_env = MagicMock()
        mock_stream_env.get_execution_environment.return_value = mock_env

        mock_t_env = MagicMock()
        mock_table_env.create.return_value = mock_t_env

        coordinator = JobCoordinator()

        # Verify environments were created
        mock_stream_env.get_execution_environment.assert_called_once()
        mock_table_env.create.assert_called_once_with(mock_env)

        assert coordinator.env == mock_env
        assert coordinator.t_env == mock_t_env
        assert coordinator.jobs == []

    @patch("src.core.job_coordinator.StreamExecutionEnvironment")
    @patch("src.core.job_coordinator.StreamTableEnvironment")
    @patch("src.core.job_coordinator.settings")
    def test_configure_flink_settings(
        self, mock_settings, mock_table_env, mock_stream_env
    ):
        """Test Flink configuration settings."""
        mock_settings.flink_parallelism = 8
        mock_settings.flink_checkpoint_interval_ms = 5000
        mock_settings.flink_idle_timeout_seconds = 60

        JobCoordinator()

        # Verify get_execution_environment was called with configuration
        call_args = mock_stream_env.get_execution_environment.call_args[0]
        assert len(call_args) == 1

        # Configuration object should have been passed
        config = call_args[0]
        assert config is not None

    @patch("src.core.job_coordinator.StreamExecutionEnvironment")
    @patch("src.core.job_coordinator.StreamTableEnvironment")
    @patch("src.core.job_coordinator.settings")
    def test_configure_table_settings(
        self, mock_settings, mock_table_env, mock_stream_env
    ):
        """Test table environment configuration."""
        mock_settings.flink_parallelism = 4
        mock_settings.flink_checkpoint_interval_ms = 10000
        mock_settings.flink_idle_timeout_seconds = 30

        mock_t_env = MagicMock()
        mock_table_env.create.return_value = mock_t_env
        mock_config = MagicMock()
        mock_t_env.get_config.return_value.get_configuration.return_value = mock_config

        JobCoordinator()

        # Verify table configuration was called
        mock_t_env.get_config.assert_called_once()
        mock_t_env.get_config.return_value.get_configuration.assert_called_once()

        # Verify configuration settings were applied
        assert mock_config.set_string.call_count >= 1

    @patch("src.core.job_coordinator.StreamExecutionEnvironment")
    @patch("src.core.job_coordinator.StreamTableEnvironment")
    @patch("src.core.job_coordinator.settings")
    def test_register_job(self, mock_settings, mock_table_env, mock_stream_env):
        """Test job registration functionality."""
        mock_settings.flink_parallelism = 4
        mock_settings.flink_checkpoint_interval_ms = 10000
        mock_settings.flink_idle_timeout_seconds = 30

        coordinator = JobCoordinator()

        # Create mock job
        mock_job = MagicMock()
        mock_job.name = "test_job"

        coordinator.register_job(mock_job)

        assert len(coordinator.jobs) == 1
        assert coordinator.jobs[0] == mock_job

    @patch("src.core.job_coordinator.StreamExecutionEnvironment")
    @patch("src.core.job_coordinator.StreamTableEnvironment")
    @patch("src.core.job_coordinator.settings")
    def test_register_multiple_jobs(
        self, mock_settings, mock_table_env, mock_stream_env
    ):
        """Test registering multiple jobs."""
        mock_settings.flink_parallelism = 4
        mock_settings.flink_checkpoint_interval_ms = 10000
        mock_settings.flink_idle_timeout_seconds = 30

        coordinator = JobCoordinator()

        # Create mock jobs
        mock_job1 = MagicMock()
        mock_job1.name = "job1"
        mock_job2 = MagicMock()
        mock_job2.name = "job2"

        coordinator.register_job(mock_job1)
        coordinator.register_job(mock_job2)

        assert len(coordinator.jobs) == 2
        assert coordinator.jobs[0] == mock_job1
        assert coordinator.jobs[1] == mock_job2

    @patch("src.core.job_coordinator.kafka_source")
    @patch("src.core.job_coordinator.kafka_sink")
    @patch("src.core.job_coordinator.StreamExecutionEnvironment")
    @patch("src.core.job_coordinator.StreamTableEnvironment")
    @patch("src.core.job_coordinator.settings")
    def test_execute_with_jobs(
        self,
        mock_settings,
        mock_table_env,
        mock_stream_env,
        mock_kafka_sink,
        mock_kafka_source,
    ):
        """Test execution with registered jobs."""
        mock_settings.flink_parallelism = 4
        mock_settings.flink_checkpoint_interval_ms = 10000
        mock_settings.flink_idle_timeout_seconds = 30

        mock_t_env = MagicMock()
        mock_table_env.create.return_value = mock_t_env
        mock_statement_set = MagicMock()
        mock_t_env.create_statement_set.return_value = mock_statement_set

        coordinator = JobCoordinator()

        # Create mock job
        mock_job = MagicMock()
        mock_job.name = "test_job"
        mock_job.sink_name = "test_sink"
        mock_pipeline = MagicMock()
        mock_job.build_pipeline.return_value = mock_pipeline

        coordinator.register_job(mock_job)
        coordinator.execute()

        # Verify connectors were registered
        mock_kafka_source.register_events_source.assert_called_once_with(mock_t_env)
        mock_kafka_sink.register_event_metrics_sink.assert_called_once_with(mock_t_env)
        mock_kafka_sink.register_session_metrics_sink.assert_called_once_with(
            mock_t_env
        )
        mock_kafka_sink.register_performance_metrics_sink.assert_called_once_with(
            mock_t_env
        )

        # Verify statement set was created and used
        mock_t_env.create_statement_set.assert_called_once()
        mock_job.build_pipeline.assert_called_once_with(mock_t_env)
        mock_statement_set.add_insert.assert_called_once_with(
            "test_sink", mock_pipeline
        )
        mock_statement_set.execute.assert_called_once()

    @patch("src.core.job_coordinator.kafka_source")
    @patch("src.core.job_coordinator.kafka_sink")
    @patch("src.core.job_coordinator.StreamExecutionEnvironment")
    @patch("src.core.job_coordinator.StreamTableEnvironment")
    @patch("src.core.job_coordinator.settings")
    def test_execute_with_no_jobs(
        self,
        mock_settings,
        mock_table_env,
        mock_stream_env,
        mock_kafka_sink,
        mock_kafka_source,
    ):
        """Test execution with no registered jobs."""
        mock_settings.flink_parallelism = 4
        mock_settings.flink_checkpoint_interval_ms = 10000
        mock_settings.flink_idle_timeout_seconds = 30

        mock_t_env = MagicMock()
        mock_table_env.create.return_value = mock_t_env
        mock_statement_set = MagicMock()
        mock_t_env.create_statement_set.return_value = mock_statement_set

        coordinator = JobCoordinator()
        coordinator.execute()

        # Verify connectors were still registered
        mock_kafka_source.register_events_source.assert_called_once_with(mock_t_env)

        # Verify statement set was created but no jobs added
        mock_t_env.create_statement_set.assert_called_once()
        mock_statement_set.add_insert.assert_not_called()
        mock_statement_set.execute.assert_called_once()

    @patch("src.core.job_coordinator.kafka_source")
    @patch("src.core.job_coordinator.kafka_sink")
    @patch("src.core.job_coordinator.StreamExecutionEnvironment")
    @patch("src.core.job_coordinator.StreamTableEnvironment")
    @patch("src.core.job_coordinator.settings")
    def test_register_connectors_called_during_execute(
        self,
        mock_settings,
        mock_table_env,
        mock_stream_env,
        mock_kafka_sink,
        mock_kafka_source,
    ):
        """Test that _register_connectors is called during execute."""
        mock_settings.flink_parallelism = 4
        mock_settings.flink_checkpoint_interval_ms = 10000
        mock_settings.flink_idle_timeout_seconds = 30

        coordinator = JobCoordinator()
        coordinator.execute()

        # Verify all connector registration methods were called
        mock_kafka_source.register_events_source.assert_called_once()
        mock_kafka_sink.register_event_metrics_sink.assert_called_once()
        mock_kafka_sink.register_session_metrics_sink.assert_called_once()
        mock_kafka_sink.register_performance_metrics_sink.assert_called_once()

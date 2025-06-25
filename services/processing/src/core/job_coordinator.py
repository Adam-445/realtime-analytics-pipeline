import logging

from pyflink.datastream import StreamExecutionEnvironment
from pyflink.table import StreamTableEnvironment
from src.core.config import settings

logger = logging.getLogger("job_coordinator")


class JobCoordinator:
    def __init__(self):
        self.env = StreamExecutionEnvironment.get_execution_environment()
        self.t_env = StreamTableEnvironment.create(self.env)
        self.jobs = []
        self._configure_environment()

    def _configure_environment(self):
        """Configure Flink environment settings"""
        self.env.set_parallelism(settings.flink_parallelism)
        self.env.enable_checkpointing(settings.checkpoint_interval_ms)

        # Configure table environment
        table_config = self.t_env.get_config()
        # Enable multi-sink optimization
        table_config.set("table.dml-sync", "false")
        table_config.set("table.exec.sink.upsert-materialize", "none")
        # Configure mini-batch for efficiency
        table_config.set("table.exec.mini-batch.enabled", "true")
        table_config.set("table.exec.mini-batch.allow-latency", "5s")
        table_config.set("table.exec.mini-batch.size", "1000")
        # Set idle timeout to prevent stalling
        table_config.set("table.exec.source.idle-timeout", "5000")

        logger.info("Flink environment configured")

    def register_job(self, job):
        """Register a job to be executed"""
        self.jobs.append(job)
        logger.info(f"Registered job: {job.name}")

    def execute(self):
        """Execute all registered jobs"""
        # Register sources and sinks
        self._register_connectors()

        # Create a statement set for multiple pipelines
        statement_set = self.t_env.create_statement_set()

        # Build and add all pipelines
        for job in self.jobs:
            pipeline = job.build_pipeline(self.t_env)
            statement_set.add_insert(job.sink_name, pipeline)
            logger.info(f"Added job pipeline: {job.name}")

        # Execute all pipelines together
        logger.info("Starting unified job execution...")
        statement_set.execute()  # Single execution call
        logger.info("Job execution completed")

    def _register_connectors(self):
        """Register all Kafka connectors"""
        from src.connectors import kafka_sink, kafka_source

        # Register source
        kafka_source.register_events_source(self.t_env)

        # Register sinks
        kafka_sink.register_event_metrics_sink(self.t_env)
        kafka_sink.register_session_metrics_sink(self.t_env)

        logger.info("Registered Kafka connectors")

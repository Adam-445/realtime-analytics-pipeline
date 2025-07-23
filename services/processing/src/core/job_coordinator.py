from pyflink.common import Configuration
from pyflink.datastream import StreamExecutionEnvironment
from pyflink.table import StreamTableEnvironment
from src.connectors import kafka_sink, kafka_source
from src.core.config import settings
from src.core.logger import get_logger

logger = get_logger("job_coordinator")


class JobCoordinator:
    def __init__(self):
        flink_conf = self._configure_flink_settings()

        self.env = StreamExecutionEnvironment.get_execution_environment(flink_conf)
        self.t_env = StreamTableEnvironment.create(self.env)

        self.jobs = []
        self._configure_table_settings()

    def _configure_flink_settings(self):
        flink_conf = Configuration()

        flink_conf.set_integer("parallelism.default", settings.flink_parallelism)

        flink_conf.set_integer(
            "execution.checkpointing.interval", settings.flink_checkpoint_interval_ms
        )

        return flink_conf

    def _configure_table_settings(self):
        table_conf = self.t_env.get_config().get_configuration()

        # Multi sink / upsert optimizations
        table_conf.set_string("table.dml-sync", "false")
        table_conf.set_string("table.exec.sink.upsert-materialize", "none")

        # Mini batch tuning
        table_conf.set_string("table.exec.mini-batch.enabled", "true")
        table_conf.set_string("table.exec.mini-batch.allow-latency", "4s")
        table_conf.set_string("table.exec.mini-batch.size", "999")

        # Idle timeouts & parallelism
        table_conf.set_string(
            "table.exec.source.idle-timeout", f"{settings.flink_idle_timeout_seconds}s"
        )
        table_conf.set_string(
            "table.exec.resource.default-parallelism", str(settings.flink_parallelism)
        )

        logger.info("Table environment configured")

    def register_job(self, job):
        """Register a job to be executed."""
        self.jobs.append(job)
        logger.info(f"Registered job: {job.name}")

    def execute(self):
        """Execute all registered jobs."""
        self._register_connectors()
        statement_set = self.t_env.create_statement_set()

        for job in self.jobs:
            pipeline = job.build_pipeline(self.t_env)
            statement_set.add_insert(job.sink_name, pipeline)
            logger.info(f"Added job pipeline: {job.name}")

        logger.info("Starting unified job execution…")
        statement_set.execute()
        logger.info("Job execution completed")

    def _register_connectors(self):
        """Register Kafka (or other) connectors."""
        kafka_source.register_events_source(self.t_env)
        kafka_sink.register_event_metrics_sink(self.t_env)
        kafka_sink.register_session_metrics_sink(self.t_env)
        kafka_sink.register_performance_metrics_sink(self.t_env)

        logger.info("Registered Kafka connectors")

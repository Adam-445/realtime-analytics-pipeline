from pyflink.table import StreamTableEnvironment, TableDescriptor
from src.core.config import settings
from src.core.schemas.event_metrics_sink import get_event_metrics_sink_schema
from src.core.schemas.performance_metrics_sink import (
    get_performance_metrics_sink_schema,
)
from src.core.schemas.session_metrics_sink import get_session_metrics_sink_schema


def register_event_metrics_sink(t_env: StreamTableEnvironment):
    t_env.create_temporary_table(
        "event_metrics",
        TableDescriptor.for_connector("kafka")
        .schema(get_event_metrics_sink_schema())
        .option("topic", settings.topic_event_metrics)
        .option("properties.bootstrap.servers", settings.kafka_bootstrap)
        .option("format", "json")
        .option("sink.transactional-id-prefix", "event-metrics-")
        .build(),
    )


def register_session_metrics_sink(t_env: StreamTableEnvironment):
    t_env.create_temporary_table(
        "session_metrics",
        TableDescriptor.for_connector("kafka")
        .schema(get_session_metrics_sink_schema())
        .option("topic", settings.topic_session_metrics)
        .option("properties.bootstrap.servers", settings.kafka_bootstrap)
        .option("format", "json")
        .option("sink.transactional-id-prefix", "session-metrics-")
        .build(),
    )


def register_performance_metrics_sink(t_env: StreamTableEnvironment):
    t_env.create_temporary_table(
        "performance_metrics",
        TableDescriptor.for_connector("kafka")
        .schema(get_performance_metrics_sink_schema())
        .option("topic", settings.topic_performance_metrics)
        .option("properties.bootstrap.servers", settings.kafka_bootstrap)
        .option("format", "json")
        .option("sink.transactional-id-prefix", "performance-metrics-")
        .build(),
    )

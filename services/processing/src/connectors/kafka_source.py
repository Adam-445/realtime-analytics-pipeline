from pyflink.table import StreamTableEnvironment, TableDescriptor
from src.core.config import settings
from src.core.schemas.event_source import get_event_source_schema


def register_events_source(t_env: StreamTableEnvironment):
    t_env.create_temporary_table(
        "events",
        TableDescriptor.for_connector("kafka")
        .schema(get_event_source_schema())
        .option("topic", settings.kafka_topic_events)
        .option("properties.bootstrap.servers", settings.kafka_bootstrap_servers)
        .option("properties.group.id", settings.processing_kafka_consumer_group)
        .option("scan.startup.mode", settings.processing_kafka_scan_startup_mode)
        .option("format", "json")
        .option("json.fail-on-missing-field", "false")
        .option("json.ignore-parse-errors", "true")
        .build(),
    )

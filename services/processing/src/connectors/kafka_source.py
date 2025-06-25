from pyflink.table import StreamTableEnvironment, TableDescriptor
from src.core.config import settings
from src.core.schemas.event_source import get_event_source_schema


def register_events_source(t_env: StreamTableEnvironment):
    t_env.create_temporary_table(
        "events",
        TableDescriptor.for_connector("kafka")
        .schema(get_event_source_schema())
        .option("topic", settings.topic_events)
        .option("properties.bootstrap.servers", settings.kafka_bootstrap)
        .option("properties.group.id", settings.kafka_group_id)
        .option("scan.startup.mode", settings.scan_startup_mode)
        .option("format", "json")
        .option("json.fail-on-missing-field", "false")
        .option("json.ignore-parse-errors", "true")
        .build(),
    )

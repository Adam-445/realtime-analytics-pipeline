import logging

from pyflink.datastream import StreamExecutionEnvironment
from pyflink.table import DataTypes, Schema, StreamTableEnvironment, TableDescriptor
from pyflink.table import expressions as expr
from pyflink.table.window import Tumble
from src.core.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("table_metric_aggregator")


def main():
    # Set up the environments
    env = StreamExecutionEnvironment.get_execution_environment()
    env.set_parallelism(2)
    t_env = StreamTableEnvironment.create(env)

    # Enable checkpointing for fault tolerance
    env.enable_checkpointing(30000)  # 30 seconds

    # Configure table environment for better debugging
    t_env.get_config().set("table.exec.mini-batch.enabled", "true")
    t_env.get_config().set("table.exec.mini-batch.allow-latency", "5s")
    t_env.get_config().set("table.exec.mini-batch.size", "1000")

    # Declare the source table
    t_env.create_temporary_table(
        "events",
        TableDescriptor.for_connector("kafka")
        .schema(
            Schema.new_builder()
            .column(
                "event",
                DataTypes.ROW(
                    [
                        DataTypes.FIELD("id", DataTypes.STRING()),
                        DataTypes.FIELD("type", DataTypes.STRING()),
                    ]
                ),
            )
            .column("user", DataTypes.ROW([DataTypes.FIELD("id", DataTypes.STRING())]))
            .column(
                "context",
                DataTypes.ROW(
                    [
                        DataTypes.FIELD("url", DataTypes.STRING()),
                        DataTypes.FIELD("referrer", DataTypes.STRING()),
                        DataTypes.FIELD("ip_address", DataTypes.STRING()),
                        DataTypes.FIELD("session_id", DataTypes.STRING()),
                    ]
                ),
            )
            .column("properties", DataTypes.MAP(DataTypes.STRING(), DataTypes.STRING()))
            .column(
                "metrics",
                DataTypes.ROW(
                    [
                        DataTypes.FIELD("load_time", DataTypes.BIGINT()),
                        DataTypes.FIELD("interaction_time", DataTypes.BIGINT()),
                    ]
                ),
            )
            .column("timestamp", DataTypes.BIGINT())
            # Create processing time attribute
            .column_by_expression("proc_time", expr.call_sql("PROCTIME()"))
            # Also create event time attribute with relaxed watermark
            .column_by_expression(
                "event_time", expr.call_sql("TO_TIMESTAMP_LTZ(`timestamp`, 3)")
            )
            .watermark("event_time", "event_time - INTERVAL '1' MINUTE")
            .build()
        )
        .option("topic", settings.topic_events)
        .option("properties.bootstrap.servers", settings.kafka_bootstrap)
        .option("properties.group.id", "flink-analytics-group")
        .option("scan.startup.mode", "earliest-offset")
        .option("format", "json")
        .option("json.fail-on-missing-field", "false")
        .option("json.ignore-parse-errors", "true")
        .build(),
    )

    # Declare the sink table for aggregated metrics
    t_env.create_temporary_table(
        "metrics",
        TableDescriptor.for_connector("kafka")
        .schema(
            Schema.new_builder()
            .column("window_start", DataTypes.TIMESTAMP_LTZ(3))
            .column("window_end", DataTypes.TIMESTAMP_LTZ(3))
            .column("event_type", DataTypes.STRING())
            .column("cnt", DataTypes.BIGINT())
            .build()
        )
        .option("topic", settings.topic_metrics)
        .option("properties.bootstrap.servers", settings.kafka_bootstrap)
        .option("format", "json")
        .build(),
    )

    # Build the processing pipeline
    events = t_env.from_path("events")

    # Now create the main aggregation pipeline using processing time windows
    aggregated_events = (
        events.select(
            expr.col("event").get("type").alias("event_type"),
            expr.col("user").get("id").alias("user_id"),
            expr.col("timestamp"),
            expr.col("proc_time"),
        )
        .filter(
            expr.col("event_type").in_(
                expr.lit("page_view"), expr.lit("click"), expr.lit("conversion")
            )
        )
        # Use processing time tumbling window (1 minute)
        .window(Tumble.over(expr.lit(1).minutes).on(expr.col("proc_time")).alias("w"))
        .group_by(expr.col("w"), expr.col("event_type"))
        .select(
            expr.col("w").start.alias("window_start"),
            expr.col("w").end.alias("window_end"),
            expr.col("event_type"),
            expr.col("event_type").count.alias("cnt"),
        )
    )

    # Execute the main aggregation job
    logger.info("Starting main aggregation job...")
    aggregated_events.execute_insert("metrics")
    logger.info("Aggregation job submitted successfully")


if __name__ == "__main__":
    main()

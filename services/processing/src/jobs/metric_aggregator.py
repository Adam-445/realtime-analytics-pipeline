import logging

from pyflink.datastream import StreamExecutionEnvironment
from pyflink.table import DataTypes, Schema, StreamTableEnvironment, TableDescriptor
from pyflink.table import expressions as expr
from pyflink.table.window import Session, Tumble
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
    # 5 seconds idle timeout
    t_env.get_config().set("table.exec.source.idle-timeout", "5000")

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
            .column(
                "device",
                DataTypes.ROW(
                    [
                        DataTypes.FIELD("user_agent", DataTypes.STRING()),
                        DataTypes.FIELD("screen_width", DataTypes.INT()),
                        DataTypes.FIELD("screen_height", DataTypes.INT()),
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
            # Also create event time attribute with relaxed watermark
            .column_by_expression(
                "event_time", expr.call_sql("TO_TIMESTAMP_LTZ(`timestamp`, 3)")
            )
            .watermark("event_time", "event_time - INTERVAL '10' SECOND")
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

    # Declare the sink tables
    t_env.create_temporary_table(
        "event_metrics",
        TableDescriptor.for_connector("kafka")
        .schema(
            Schema.new_builder()
            .column("window_start", DataTypes.TIMESTAMP_LTZ(3))
            .column("window_end", DataTypes.TIMESTAMP_LTZ(3))
            .column("event_type", DataTypes.STRING())
            .column("event_count", DataTypes.BIGINT())
            .column("user_count", DataTypes.BIGINT())
            .build()
        )
        .option("topic", "event_metrics")
        .option("properties.bootstrap.servers", settings.kafka_bootstrap)
        .option("format", "json")
        .build(),
    )

    t_env.create_temporary_table(
        "session_metrics",
        TableDescriptor.for_connector("kafka")
        .schema(
            Schema.new_builder()
            .column("session_id", DataTypes.STRING())
            .column("user_id", DataTypes.STRING())
            .column("start_time", DataTypes.TIMESTAMP_LTZ(3))
            .column("end_time", DataTypes.TIMESTAMP_LTZ(3))
            .column("duration", DataTypes.BIGINT())
            .column("page_count", DataTypes.BIGINT())
            .column("device_type", DataTypes.STRING())
            .build()
        )
        .option("topic", "session_metrics")
        .option("properties.bootstrap.servers", settings.kafka_bootstrap)
        .option("format", "json")
        .build(),
    )

    # Build the processing pipeline
    events = t_env.from_path("events")

    # Event aggregation
    event_aggregation = (
        events.select(
            expr.col("event_time"),
            expr.col("event").get("type").alias("event_type"),
            expr.col("user").get("id").alias("user_id"),
            # Categorise devices
            expr.col("device")
            .get("user_agent")
            .like("%Mobile%")
            .then("Mobile", "Desktop")
            .alias("device_category"),
        )
        .filter(
            expr.col("event_type").in_(
                "page_view", "click", "conversion", "add_to_cart"
            )
        )
        # Use processing time tumbling window (1 minute)
        .window(Tumble.over(expr.lit(1).minutes).on(expr.col("event_time")).alias("w"))
        .group_by(expr.col("w"), expr.col("event_type"))
        .select(
            expr.col("w").start.alias("window_start"),
            expr.col("w").end.alias("window_end"),
            expr.col("event_type"),
            expr.col("user_id").count.distinct.alias("user_count"),
            expr.col("event_type").count.alias("event_count"),
        )
    )

    # Session Tracking
    session_base = (
        events.select(
            expr.col("event").get("type").alias("event_type"),
            expr.col("event_time"),
            expr.col("context").get("session_id").alias("session_id"),
            expr.col("user").get("id").alias("user_id"),
            expr.col("device")
            .get("user_agent")
            .like("%Mobile%")
            .then("Mobile", "Desktop")
            .alias("device_type"),
        )
        .filter(expr.col("event_type") == "page_view")
        .window(
            Session.with_gap(expr.lit(30).minutes).on(expr.col("event_time")).alias("w")
        )
        .group_by(expr.col("session_id"), expr.col("user_id"), expr.col("w"))
        .select(
            expr.col("session_id"),
            expr.col("user_id"),
            expr.col("w").start.cast(DataTypes.TIMESTAMP_LTZ(3)).alias("start_time"),
            expr.col("w").end.cast(DataTypes.TIMESTAMP_LTZ(3)).alias("end_time"),
            # Calculate duration using a computed column approach
            expr.lit(0).alias(
                "duration"
            ),  # Placeholder - will be calculated in post-processing
            expr.col("session_id").count.alias("page_count"),
            expr.col("device_type").max.alias("device_type"),
        )
    )

    # Calculate duration in a separate step
    session_aggregation = session_base.select(
        expr.col("session_id"),
        expr.col("user_id"),
        expr.col("start_time"),
        expr.col("end_time"),
        # Calculate duration in milliseconds using TIMESTAMPDIFF
        expr.call_sql("TIMESTAMPDIFF(MILLISECOND, start_time, end_time)").alias(
            "duration"
        ),
        expr.col("page_count"),
        expr.col("device_type"),
    )

    # Execute the analytics jobs
    logger.info("Starting event aggregation job...")
    event_aggregation.execute_insert("event_metrics")

    logger.info("Starting session tracking job...")
    session_aggregation.execute_insert("session_metrics")

    logger.info("All analytics jobs submitted successfully")


if __name__ == "__main__":
    main()

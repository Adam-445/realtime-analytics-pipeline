from pyflink.table import DataTypes
from pyflink.table import expressions as expr
from pyflink.table.window import Session
from src.core.config import settings
from src.jobs.base_job import BaseJob
from src.transformations import device_categorizer


class SessionTracker(BaseJob):
    def __init__(self):
        super().__init__("SessionTracker", "session_metrics")

    def build_pipeline(self, t_env):
        events = t_env.from_path("events")
        categorized = device_categorizer.categorize_device(events)

        session_base = (
            categorized.select(
                expr.col("event").get("type").alias("event_type"),
                expr.col("event_time"),
                expr.col("context").get("session_id").alias("session_id"),
                expr.col("user").get("id").alias("user_id"),
                expr.col("device_category"),
            )
            .filter(expr.col("event_type") == "page_view")
            .window(
                Session.with_gap(expr.lit(settings.session_gap_seconds).seconds)
                .on(expr.col("event_time"))
                .alias("w")
            )
            .group_by(expr.col("session_id"), expr.col("user_id"), expr.col("w"))
            .select(
                expr.col("session_id"),
                expr.col("user_id"),
                expr.col("w")
                .start.cast(DataTypes.TIMESTAMP_LTZ(3))
                .alias("start_time"),
                expr.col("w").end.cast(DataTypes.TIMESTAMP_LTZ(3)).alias("end_time"),
                expr.col("session_id").count.alias("page_count"),
                expr.col("device_category").max.alias("device_category"),
            )
        )

        return session_base.select(
            expr.col("session_id"),
            expr.col("user_id"),
            expr.col("start_time"),
            expr.col("end_time"),
            expr.call_sql("TIMESTAMPDIFF(MILLISECOND, start_time, end_time)").alias(
                "duration"
            ),
            expr.col("page_count"),
            expr.col("device_category"),
        )

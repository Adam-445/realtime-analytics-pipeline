from pyflink.table import expressions as expr
from pyflink.table.window import Tumble
from src.core.config import settings
from src.jobs.base_job import BaseJob
from src.transformations import device_categorizer


class EventAggregator(BaseJob):
    def __init__(self):
        super().__init__("EventAggregator", "event_metrics")

    def build_pipeline(self, t_env):
        events = t_env.from_path("events")
        categorized = device_categorizer.categorize_device(events)
        time_col = "event_time" if settings.environment == "production" else "proc_time"

        return (
            categorized.select(
                expr.col(time_col),
                expr.col("event").get("type").alias("event_type"),
                expr.col("user").get("id").alias("user_id"),
                expr.col("device_category"),
            )
            .filter(expr.col("event_type").in_(*settings.allowed_event_types))
            .window(
                Tumble.over(expr.lit(settings.metrics_window_size_seconds).seconds)
                .on(expr.col(time_col))
                .alias("w")
            )
            .group_by(expr.col("w"), expr.col("event_type"))
            .select(
                expr.col("w").start.alias("window_start"),
                expr.col("w").end.alias("window_end"),
                expr.col("event_type"),
                expr.col("event_type").count.alias("event_count"),
                expr.col("user_id").count.distinct.alias("user_count"),
            )
        )

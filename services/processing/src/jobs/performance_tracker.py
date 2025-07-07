from pyflink.table import expressions as expr
from pyflink.table.window import Tumble
from src.core.config import settings
from src.jobs.base_job import BaseJob
from src.transformations import device_categorizer


class PerformanceTracker(BaseJob):
    def __init__(self):
        super().__init__("PerformanceTracker", "performance_metrics")

    def build_pipeline(self, t_env):
        events = t_env.from_path("events")
        categorized = device_categorizer.categorize_device(events)

        return (
            categorized.select(
                expr.col("event").get("type").alias("event_type"),
                expr.col("event_time"),
                expr.col("device_category"),
                expr.col("metrics").get("load_time").alias("load_time"),
            )
            .filter(expr.col("event_type") == "page_view")
            .filter(expr.col("load_time").is_not_null)
            .window(
                Tumble.over(expr.lit(settings.performance_window_size_seconds).seconds)
                .on(expr.col("event_time"))
                .alias("w")
            )
            .group_by(expr.col("device_category"), expr.col("w"))
            .select(
                expr.col("w").start.alias("window_start"),
                expr.col("w").end.alias("window_end"),
                expr.col("device_category"),
                expr.col("load_time").avg.alias("avg_load_time"),
                expr.col("load_time").percentile(0.95).alias("p95_load_time"),
            )
        )

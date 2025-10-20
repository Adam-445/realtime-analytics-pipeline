# Adding a New Processing Job

This guide explains how to add a new Flink job to the processing service and wire it end-to-end.

- Related: [Processing Service Setup](../../setup/services/processing.md)
- See also: [Modules Overview](../README.md)

## Steps

1. Create the Job Class under `services/processing/src/jobs/`:

```python
from src.jobs.base_job import BaseJob
from pyflink.table import expressions as expr
from src.core.config import settings

class ProcessingMetricsJob(BaseJob):
    def __init__(self):
        super().__init__("ProcessingMetrics", "processing_metrics")
    
    def build_pipeline(self, t_env):
        events = t_env.from_path("events")
        
        return (
            events
            .select(
                expr.col("event_time"),
                expr.col("event").get("type").alias("event_type"),
                expr.call_sql("CURRENT_WATERMARK(event_time)").alias("watermark")
            )
            .group_by(expr.col("event_type"))
            .select(
                expr.col("event_type"),
                expr.col("watermark").max.alias("max_watermark"),
                expr.count("*").alias("event_count")
            )
        )
```

2. Create Sink Schema in `services/processing/src/core/schemas/processing_metrics_sink.py`:

```python
from pyflink.table import DataTypes, Schema

def get_processing_metrics_sink_schema():
    return (
        Schema.new_builder()
        .column("event_type", DataTypes.STRING())
        .column("max_watermark", DataTypes.TIMESTAMP_LTZ(3))
        .column("event_count", DataTypes.BIGINT())
        .build()
    )
```

3. Register the Sink in `services/processing/src/connectors/kafka_sink.py`:

```python
from core.schemas.processing_metrics_sink import get_processing_metrics_sink_schema


def register_processing_metrics_sink(t_env: StreamTableEnvironment):
    t_env.create_temporary_table(
        "processing_metrics",
        TableDescriptor.for_connector("kafka")
        .schema(get_processing_metrics_sink_schema())
        .option("topic", settings.topic_processing_metrics)
        .build(),
    )
```

Then in `services/processing/src/core/job_coordinator.py`:

```python
def _register_connectors(self):
    ...
    kafka_sink.register_processing_metrics_sink(self.t_env)
```

4. Update Configuration in `services/processing/src/core/config.py`:

```python
class Settings(BaseSettings):
    topic_processing_metrics: str = "processing_metrics"
    metrics_window_minutes: int = 5
```

5. Register the Job in `services/processing/src/main.py`:

```python
from src.jobs.processing_metrics import ProcessingMetricsJob

def main():
    ...
    coordinator.register_job(ProcessingMetricsJob())
```

6. Create Kafka Topic (if auto-creation is not used): update ingestion admin (or dedicated topic admin):

```python
def create_topics():
    ...
    topics.append(NewTopic(settings.topic_processing_metrics, num_partitions=3, replication_factor=1))
```

## Design Principles

- Single responsibility per job
- Reuse common transformations (e.g., `device_categorizer`)
- Watermark-aware and event-time first
- Config-driven windows and thresholds
- Robust error handling for complex pipelines

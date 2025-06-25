## Adding a New Job to the Real-time Analytics Pipeline

### Step 1: Create the Job Class
Create a new Python file in `src/jobs/` (e.g., `processing_metrics.py`):

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

### Step 2: Create Sink Schema
Add a schema definition in `src/core/schemas/processing_metrics_sink.py`:

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

### Step 3: Register the Sink
Update `src/connectors/kafka_sink.py`:

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

Then in `src/core/job_coordinator.py` update _register_connectors in JobCoordinator:
```python
def _register_connectors(self):
    ...
    kafka_sink.register_processing_metrics_sink(self.t_env)
```

### Step 4: Update Configuration
Add to `src/core/config.py`:

```python
class Settings(BaseSettings):
    # Add new topic
    topic_processing_metrics: str = "processing_metrics"
    
    # Add new config parameters if needed
    metrics_window_minutes: int = 5
```

### Step 5: Register the Job
Update `src/main.py`:

```python
from src.jobs.processing_metrics import ProcessingMetricsJob

def main():
    ...
    coordinator.register_job(ProcessingMetricsJob())
```

### Step 6: Create Kafka Topic
Update topic creation in ingestion service (`src/infrastructure/kafka/admin.py`):

```python
def create_topics():
    ...
    topics.append(
        NewTopic(settings.topic_processing_metrics, num_partitions=3, replication_factor=1)
    )
```

---

### Key Design Principles for New Jobs:
1. **Single Responsibility**: Each job should focus on one specific metric or analysis
2. **Reuse Transformations**: Share common transformations like `device_categorizer`
3. **Watermark Awareness**: Always consider event time and watermarks
4. **Config-Driven**: Make window sizes, thresholds, etc. configurable
5. **Error Handling**: Add robust error handling in complex jobs
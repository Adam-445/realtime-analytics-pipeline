from pyflink.table import DataTypes, Schema


def get_performance_metrics_sink_schema():
    return (
        Schema.new_builder()
        .column("window_start", DataTypes.TIMESTAMP_LTZ(3))
        .column("window_end", DataTypes.TIMESTAMP_LTZ(3))
        .column("device_category", DataTypes.STRING())
        .column("avg_load_time", DataTypes.DOUBLE())
        .column("p95_load_time", DataTypes.DOUBLE())
        .build()
    )

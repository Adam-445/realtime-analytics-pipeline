from pyflink.table import DataTypes, Schema


def get_event_metrics_sink_schema():
    return (
        Schema.new_builder()
        .column("window_start", DataTypes.TIMESTAMP_LTZ(3))
        .column("window_end", DataTypes.TIMESTAMP_LTZ(3))
        .column("event_type", DataTypes.STRING())
        .column("event_count", DataTypes.BIGINT())
        .column("user_count", DataTypes.BIGINT())
        .build()
    )

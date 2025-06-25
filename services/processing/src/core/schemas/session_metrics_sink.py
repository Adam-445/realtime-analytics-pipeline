from pyflink.table import DataTypes, Schema


def get_session_metrics_sink_schema():
    return (
        Schema.new_builder()
        .column("session_id", DataTypes.STRING())
        .column("user_id", DataTypes.STRING())
        .column("start_time", DataTypes.TIMESTAMP_LTZ(3))
        .column("end_time", DataTypes.TIMESTAMP_LTZ(3))
        .column("duration", DataTypes.BIGINT())
        .column("page_count", DataTypes.BIGINT())
        .column("device_category", DataTypes.STRING())
        .build()
    )

from pyflink.table import DataTypes, Schema


def get_event_source_schema():
    return (
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
        .column_by_expression("event_time", "TO_TIMESTAMP_LTZ(`timestamp`, 3)")
        .watermark("event_time", "event_time - INTERVAL '10' SECOND")
        .build()
    )

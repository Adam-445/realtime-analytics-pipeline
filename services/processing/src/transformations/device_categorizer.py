from pyflink.table import expressions as expr


def categorize_device(table):
    return table.add_columns(
        expr.col("device")
        .get("user_agent")
        .like("%Mobile%")
        .then("Mobile", "Desktop")
        .alias("device_category")
    )

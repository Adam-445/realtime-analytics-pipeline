from pyflink.table import expressions as expr


def categorize_device(table):
    return table.add_columns(
        expr.case()
        .when(expr.col("device").get("user_agent").like("%Mobile%"), "Mobile")
        .when(expr.col("device").get("user_agent").like("%Tablet%"), "Tablet")
        .when(expr.col("device").get("user_agent").like("%Bot%"), "Bot")
        .else_value("Desktop")
        .alias("device_category")
    )

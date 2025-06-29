from pyflink.table import expressions as expr


def categorize_device(table):
    ua = expr.col("device").get("user_agent")
    category = (
        ua.like("%Mobile%").then(
            "Mobile",
            ua.like("%Tablet%").then("Tablet", ua.like("%Bot%").then("Bot", "Desktop")),
        )
    ).alias("device_category")

    return table.add_columns(category)

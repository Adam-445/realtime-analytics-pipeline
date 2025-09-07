from shared.constants.topics import Topics


def debug_database_state(
    clickhouse_client, print_tables: bool = False, tables: list | None = None
):
    """
    Helper function to debug the current state of all tables
    """
    if not tables:
        tables = [
            Topics.EVENT_METRICS,
            Topics.SESSION_METRICS,
            Topics.PERFORMANCE_METRICS,
        ]

    for table in tables:
        try:
            count_query = f"SELECT COUNT(*) FROM {table}"
            count_result = clickhouse_client.execute(count_query)
            print(f"\n{table} - Total rows: {count_result[0][0]}")

            if print_tables and count_result[0][0] > 0:
                sample_query = f"SELECT * FROM {table} LIMIT 5"
                sample_result = clickhouse_client.execute(sample_query)
                print(f"{table} - Sample data: {sample_result}")

        except Exception as e:
            print(f"Error querying {table}: {e}")

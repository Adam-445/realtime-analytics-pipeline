from datetime import datetime, timedelta
from typing import Any, Dict, List

import clickhouse_connect
from src.core.config import settings
from src.core.logger import get_logger

logger = get_logger("clickhouse_client")


class ClickHouseCacheWarmer:
    def __init__(self):
        self.client = clickhouse_connect.get_client(
            host=settings.clickhouse_host,
            port=settings.clickhouse_port,
            database=settings.clickhouse_db,
            username=settings.clickhouse_user,
            password=settings.clickhouse_password,
            interface="http",  # Use HTTP interface explicitly
        )

    async def warm_event_metrics(self) -> List[Dict[str, Any]]:
        """Fetch recent event metrics for cache warming"""
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=settings.cache_warming_window_hours)

        query = """
        SELECT
            window_start,
            window_end,
            event_type,
            event_count,
            user_count
        FROM event_metrics
        WHERE window_start >= %(start_time)s
        AND window_start <= %(end_time)s
        ORDER BY window_start DESC
        LIMIT %(limit)s
        """

        try:
            result = self.client.query(
                query,
                parameters={
                    "start_time": start_time,
                    "end_time": end_time,
                    "limit": settings.cache_warming_batch_size,
                },
            )

            metrics = []
            for row in result.result_rows:
                metrics.append(
                    {
                        "window_start": row[0],
                        "window_end": row[1],
                        "event_type": row[2],
                        "event_count": row[3],
                        "user_count": row[4],
                        "metric_type": "event_metrics",
                    }
                )

            logger.info(
                "Fetched event metrics for warming",
                extra={
                    "count": len(metrics),
                    "start_time": start_time,
                    "end_time": end_time,
                },
            )
            return metrics

        except Exception as e:
            logger.error("Failed to fetch event metrics", extra={"error": str(e)})
            return []

    async def warm_session_metrics(self) -> List[Dict[str, Any]]:
        """Fetch recent session metrics for cache warming"""
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=settings.cache_warming_window_hours)

        query = """
        SELECT
            session_id,
            user_id,
            start_time,
            end_time,
            duration,
            page_count,
            device_category
        FROM session_metrics
        WHERE start_time >= %(start_time)s
        AND start_time <= %(end_time)s
        ORDER BY start_time DESC
        LIMIT %(limit)s
        """

        try:
            result = self.client.query(
                query,
                parameters={
                    "start_time": start_time,
                    "end_time": end_time,
                    "limit": settings.cache_warming_batch_size,
                },
            )

            metrics = []
            for row in result.result_rows:
                metrics.append(
                    {
                        "session_id": row[0],
                        "user_id": row[1],
                        "start_time": row[2],
                        "end_time": row[3],
                        "duration": row[4],
                        "page_count": row[5],
                        "device_category": row[6],
                        "metric_type": "session_metrics",
                    }
                )

            logger.info(
                "Fetched session metrics for warming",
                extra={
                    "count": len(metrics),
                    "start_time": start_time,
                    "end_time": end_time,
                },
            )
            return metrics

        except Exception as e:
            logger.error("Failed to fetch session metrics", extra={"error": str(e)})
            return []

    async def warm_performance_metrics(self) -> List[Dict[str, Any]]:
        """Fetch recent performance metrics for cache warming"""
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=settings.cache_warming_window_hours)

        query = """
        SELECT
            window_start,
            window_end,
            device_category,
            avg_load_time,
            p95_load_time
        FROM performance_metrics
        WHERE window_start >= %(start_time)s
        AND window_start <= %(end_time)s
        ORDER BY window_start DESC
        LIMIT %(limit)s
        """

        try:
            result = self.client.query(
                query,
                parameters={
                    "start_time": start_time,
                    "end_time": end_time,
                    "limit": settings.cache_warming_batch_size,
                },
            )

            metrics = []
            for row in result.result_rows:
                metrics.append(
                    {
                        "window_start": row[0],
                        "window_end": row[1],
                        "device_category": row[2],
                        "avg_load_time": row[3],
                        "p95_load_time": row[4],
                        "metric_type": "performance_metrics",
                    }
                )

            logger.info(
                "Fetched performance metrics for warming",
                extra={
                    "count": len(metrics),
                    "start_time": start_time,
                    "end_time": end_time,
                },
            )
            return metrics

        except Exception as e:
            logger.error("Failed to fetch performance metrics", extra={"error": str(e)})
            return []

    async def get_historical_event_count(
        self, dimensions: Dict[str, str], window_seconds: int
    ) -> int:
        """Fallback to ClickHouse for historical event count data"""
        end_time = datetime.now()
        start_time = end_time - timedelta(seconds=window_seconds)

        # Build WHERE clause based on dimensions
        where_conditions = [
            "window_start >= %(start_time)s",
            "window_start <= %(end_time)s",
        ]
        params: Dict[str, Any] = {"start_time": start_time, "end_time": end_time}

        if "event_type" in dimensions:
            where_conditions.append("event_type = %(event_type)s")
            params["event_type"] = dimensions["event_type"]

        where_clause = " AND ".join(where_conditions)

        query = f"""
        SELECT SUM(event_count) as total_events
        FROM event_metrics
        WHERE {where_clause}
        """

        try:
            result = self.client.query(query, parameters=params)
            total = result.result_rows[0][0] if result.result_rows else 0
            logger.debug(
                "Historical event count fetched",
                extra={
                    "dimensions": dimensions,
                    "window_seconds": window_seconds,
                    "total": total,
                },
            )
            return int(total or 0)

        except Exception as e:
            logger.error(
                "Failed to fetch historical event count", extra={"error": str(e)}
            )
            return 0

    def close(self):
        """Close the ClickHouse client connection"""
        try:
            self.client.close()
        except Exception as e:
            logger.warning("Error closing ClickHouse client", extra={"error": str(e)})

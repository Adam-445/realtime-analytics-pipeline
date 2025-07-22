import logging
import time

from fastapi import APIRouter, Depends, status
from prometheus_client import Counter, Histogram
from src.api.v1.dependencies import get_kafka_producer
from src.infrastructure.kafka.producer import EventProducer
from src.schemas.analytics_event import AnalyticsEvent

INGESTION_REQUESTS = Counter("ingestion_requests_total", "Total API Requests")
INGESTION_LATENCY = Histogram("ingestion_request_latency_seconds", "Request latency")
KAFKA_PRODUCER_ERRORS = Counter("kafka_producer_errors_total", "Kafka producer errors")

router = APIRouter()


@router.post(
    "/track",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Track analytics event",
    response_description="Event accepted for processing",
)
async def track_event(
    event: AnalyticsEvent, producer: EventProducer = Depends(get_kafka_producer)
):
    logger = logging.getLogger("api.track")
    start_time = time.time()

    logger.info(
        "Received analytics event",
        extra={
            "event_id": str(event.event.id),
            "event_type": event.event.type,
            "user_id": event.user.id,
            "session_id": event.context.session_id,
        },
    )

    INGESTION_REQUESTS.inc()
    try:
        await producer.send_event(event)
        elapsed = time.time() - start_time
        logger.info(
            "Event processed successfully",
            extra={
                "processing_time": elapsed,
                "event_type": event.event.type,
                "event_id": str(event.event.id),
            },
        )
        return {"status": "accepted"}

    except Exception as e:
        KAFKA_PRODUCER_ERRORS.inc()
        elapsed = time.time() - start_time
        logger.error(
            "Failed to process event",
            extra={
                "error": str(e),
                "event_type": event.event.type,
                "event_id": str(event.event.id),
                "processing_time": elapsed,
            },
        )
        raise

    finally:
        INGESTION_LATENCY.observe(time.time() - start_time)

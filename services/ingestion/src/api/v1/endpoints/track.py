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
    start_time = time.time()
    INGESTION_REQUESTS.inc()
    try:
        await producer.send_event(event)
        return {"status": "accepted"}
    except Exception:
        KAFKA_PRODUCER_ERRORS.inc()
        raise
    finally:
        INGESTION_LATENCY.observe(time.time() - start_time)

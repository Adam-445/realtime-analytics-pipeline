from fastapi import APIRouter, Depends, status
from src.api.v1.dependencies import get_kafka_producer
from src.infrastructure.kafka.producer import EventProducer
from src.schemas.analytics_event import AnalyticsEvent

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
    await producer.send_event(event)
    return {"status": "accepted"}

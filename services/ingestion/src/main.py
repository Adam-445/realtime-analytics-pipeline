from contextlib import asynccontextmanager

from fastapi import FastAPI
from src.api.v1.dependencies import get_kafka_producer
from src.api.v1.endpoints import track
from src.core.logging_config import configure_logging
from src.startup import initialize_application


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    initialize_application()
    try:
        yield
    finally:
        producer = get_kafka_producer()
        producer.flush()


app = FastAPI(
    title="Real-time Analytics Ingestion API", version="0.2.2", lifespan=lifespan
)

# Include routers
app.include_router(track.router, prefix="/v1/analytics")

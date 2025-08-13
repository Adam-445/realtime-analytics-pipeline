from contextlib import asynccontextmanager

from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator
from src.api.v1.dependencies import get_kafka_producer
from src.api.v1.router import api_router
from src.startup import initialize_application


@asynccontextmanager
async def lifespan(app: FastAPI):
    initialize_application()
    try:
        yield
    finally:
        producer = get_kafka_producer()
        producer.flush()


app = FastAPI(
    title="Real-time Analytics Ingestion API", version="0.2.2", lifespan=lifespan
)

instrumentator = Instrumentator(
    should_group_status_codes=True,
    should_ignore_untemplated=True,
    excluded_handlers=["/docs", "/openapi.json", "/metrics"],
    inprogress_name="ingestion_inprogress",
    inprogress_labels=True,
)
instrumentator.instrument(app).expose(app)

app.include_router(api_router, prefix="/v1")

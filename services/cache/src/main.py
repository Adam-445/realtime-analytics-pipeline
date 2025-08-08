from contextlib import asynccontextmanager

from fastapi import FastAPI
from prometheus_client import make_asgi_app
from src.api.v1.routes import health, metrics
from src.infrastructure.kafka.consumer import MetricsConsumer
from src.infrastructure.kafka.flink_consumer import FlinkMetricsConsumer
from src.startup import initialize_application


@asynccontextmanager
async def lifespan(app: FastAPI):
    await initialize_application()

    # Start raw events consumer
    raw_consumer = MetricsConsumer()
    raw_consumer.start()

    # Start Flink metrics consumer
    flink_consumer = FlinkMetricsConsumer()
    flink_consumer.start()

    try:
        yield
    finally:
        raw_consumer.stop()
        flink_consumer.stop()


app = FastAPI(
    title="Real-time Metrics Cache API",
    version="0.2.0",
    description="Multi-layer caching service for real-time analytics pipeline",
    lifespan=lifespan,
)

# Include metrics endpoint
app.include_router(metrics.router, prefix="/v1/metrics", tags=["metrics"])
app.include_router(health.router, prefix="/v1", tags=["health"])

# Expose Prometheus metrics under /internal/metrics
prometheus_app = make_asgi_app()
app.mount("/internal/metrics", prometheus_app)

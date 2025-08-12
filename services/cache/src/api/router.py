from fastapi import APIRouter

from .endpoints import health, metrics

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(metrics.router)

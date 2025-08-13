from fastapi import APIRouter

from .endpoints import health, track

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(track.router)

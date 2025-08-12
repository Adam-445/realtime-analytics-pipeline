from fastapi import APIRouter, Depends
from src.api.dependencies import get_cache_service
from src.services.cache_service import CacheService

router = APIRouter(prefix="/metrics")


@router.get("/event/latest")
async def event_latest(svc: CacheService = Depends(get_cache_service)):
    return await svc.get_event_latest()


@router.get("/event/windows")
async def event_windows(
    limit: int = 20, svc: CacheService = Depends(get_cache_service)
):
    windows = await svc.get_event_windows(limit)
    return {"windows": windows}


@router.get("/performance/windows")
async def performance_windows(
    limit: int = 20, svc: CacheService = Depends(get_cache_service)
):
    windows = await svc.get_performance_windows(limit)
    return {"windows": windows}


@router.get("/overview")
async def overview(svc: CacheService = Depends(get_cache_service)):
    return await svc.get_overview()

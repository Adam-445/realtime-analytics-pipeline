from fastapi import Depends, Request
from src.infrastructure.redis.repository import CacheRepository
from src.services.cache_service import CacheService


def get_repo(request: Request) -> CacheRepository:
    return request.app.state.repo  # type: ignore[return-value]


def get_cache_service(repo: CacheRepository = Depends(get_repo)) -> CacheService:
    return CacheService(repo)

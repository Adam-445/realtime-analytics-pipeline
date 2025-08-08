from src.core.config import settings
from src.core.logger import get_logger
from src.core.logging_config import configure_logging

logger = get_logger("startup")


async def initialize_application():
    configure_logging()
    logger.info(
        "Enhanced Cache service initializing",
        extra={"service": settings.otel_service_name},
    )

    # Initialize cache warming if enabled
    if settings.enable_cache_warming:
        logger.info("Cache warming enabled, initializing ClickHouse client")
        try:
            from src.services.cache_warming import CacheWarmingService

            cache_warmer = CacheWarmingService()
            await cache_warmer.warm_cache_on_startup()
            cache_warmer.cleanup()
        except Exception as e:
            logger.warning(
                "Cache warming failed during startup", extra={"error": str(e)}
            )
    else:
        logger.info("Cache warming disabled, skipping ClickHouse initialization")

    logger.info("Enhanced Cache service initialization complete")

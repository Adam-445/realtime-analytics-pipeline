from src.core.job_coordinator import JobCoordinator
from src.core.logger import get_logger
from src.jobs.event_aggregator import EventAggregator
from src.jobs.performance_tracker import PerformanceTracker
from src.jobs.session_tracker import SessionTracker

try:
    from shared.logging.json import configure_logging as shared_configure_logging
except ImportError:
    shared_configure_logging = None


def main():
    # Configure logging using shared implementation
    if shared_configure_logging:
        from src.core.config import settings

        shared_configure_logging(
            service=settings.otel_service_name,
            level=settings.app_log_level,
            environment=settings.app_environment,
            redaction_patterns=settings.app_log_redaction_patterns,
        )
    logger = get_logger("main")
    logger.info("Starting Real-time Analytics Pipeline")

    # Initialize coordinator
    coordinator = JobCoordinator()

    # Register jobs
    coordinator.register_job(EventAggregator())
    coordinator.register_job(SessionTracker())
    coordinator.register_job(PerformanceTracker())

    # Execute all jobs
    coordinator.execute()
    logger.info("Pipeline execution completed")


if __name__ == "__main__":
    main()

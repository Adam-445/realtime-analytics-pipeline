from src.core.job_coordinator import JobCoordinator
from src.core.logger import get_logger
from src.core.logging_config import configure_logging
from src.core.tracing import configure_tracing
from src.jobs.event_aggregator import EventAggregator
from src.jobs.performance_tracker import PerformanceTracker
from src.jobs.session_tracker import SessionTracker


def main():
    configure_logging()
    configure_tracing()
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

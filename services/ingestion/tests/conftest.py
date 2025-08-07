import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from src.main import app


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_kafka_producer():
    """Mock Kafka producer for testing."""
    from src.api.v1.dependencies import get_kafka_producer
    from src.main import app

    # Clear the cache first
    get_kafka_producer.cache_clear()

    # Create mock producer
    mock_producer = MagicMock()
    mock_producer.send_event = AsyncMock()
    mock_producer.flush = MagicMock()

    # Override the dependency
    def get_mock_producer():
        return mock_producer

    app.dependency_overrides[get_kafka_producer] = get_mock_producer

    yield mock_producer

    # Clean up
    app.dependency_overrides.clear()
    get_kafka_producer.cache_clear()


@pytest.fixture
def test_client():
    """FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def sample_analytics_event():
    """Sample analytics event for testing."""
    return {
        "event": {"type": "page_view"},
        "user": {"id": "user123"},
        "device": {
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36",
            "screen_width": 1920,
            "screen_height": 1080,
        },
        "context": {
            "url": "https://example.com/page",
            "referrer": "https://example.com/home",
            "session_id": "session123",
        },
        "metrics": {"load_time": 250, "interaction_time": 1500},
        "properties": {"page_title": "Example Page", "category": "marketing"},
    }


@pytest.fixture
def sample_event_dict():
    """Sample event as dictionary for JSON testing."""
    return {
        "event": {"type": "page_view"},
        "user": {"id": "user123"},
        "device": {
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36",
            "screen_width": 1920,
            "screen_height": 1080,
        },
        "context": {
            "url": "https://example.com/page",
            "referrer": "https://example.com/home",
            "session_id": "session123",
        },
        "metrics": {"load_time": 250, "interaction_time": 1500},
        "properties": {"page_title": "Example Page", "category": "marketing"},
    }


@pytest.fixture
def mock_logger():
    """Mock logger for testing."""
    with patch("src.api.v1.endpoints.track.get_logger") as mock_get_logger:
        mock_logger_instance = MagicMock()
        mock_get_logger.return_value = mock_logger_instance
        yield mock_logger_instance


@pytest.fixture
def mock_settings():
    """Mock settings for testing."""
    with patch("src.core.config.settings") as mock_settings:
        mock_settings.kafka_bootstrap_servers = "localhost:9092"
        mock_settings.kafka_topic_events = "test_analytics_events"
        mock_settings.app_log_level = "DEBUG"
        yield mock_settings


@pytest.fixture
def mock_prometheus_metrics():
    """Mock Prometheus metrics for testing."""
    with patch("src.api.v1.endpoints.track.INGESTION_REQUESTS") as mock_requests, patch(
        "src.api.v1.endpoints.track.INGESTION_LATENCY"
    ) as mock_latency, patch(
        "src.api.v1.endpoints.track.KAFKA_PRODUCER_ERRORS"
    ) as mock_errors:
        yield {
            "requests": mock_requests,
            "latency": mock_latency,
            "errors": mock_errors,
        }

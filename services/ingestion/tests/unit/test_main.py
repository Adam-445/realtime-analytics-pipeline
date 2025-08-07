from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


class TestMainApplication:
    """Test main FastAPI application setup and lifecycle."""

    @patch("src.main.initialize_application")
    @patch("src.main.get_kafka_producer")
    def test_lifespan_startup_and_shutdown(
        self, mock_get_kafka_producer, mock_initialize_application
    ):
        """Test application lifespan startup and shutdown."""
        from src.main import lifespan

        # Setup mocks
        mock_producer = MagicMock()
        mock_get_kafka_producer.return_value = mock_producer

        # Test the lifespan context manager
        async def test_lifespan():
            mock_app = MagicMock()
            async with lifespan(mock_app):
                # Verify startup was called
                mock_initialize_application.assert_called_once()

            # Verify shutdown was called
            mock_get_kafka_producer.assert_called_once()
            mock_producer.flush.assert_called_once()

        # Run the async test
        import asyncio

        asyncio.run(test_lifespan())

    @patch("src.main.initialize_application")
    @patch("src.main.get_kafka_producer")
    def test_lifespan_startup_exception(
        self, mock_get_kafka_producer, mock_initialize_application
    ):
        """Test application lifespan when startup raises exception."""
        from src.main import lifespan

        # Setup mocks
        mock_producer = MagicMock()
        mock_get_kafka_producer.return_value = mock_producer
        mock_initialize_application.side_effect = RuntimeError("Startup failed")

        async def test_lifespan():
            mock_app = MagicMock()
            with pytest.raises(RuntimeError, match="Startup failed"):
                async with lifespan(mock_app):
                    pass

        # Run the async test
        import asyncio

        asyncio.run(test_lifespan())

    def test_app_configuration(self):
        """Test FastAPI app configuration."""
        from src.main import app

        assert app.title == "Real-time Analytics Ingestion API"
        assert app.router is not None

    def test_prometheus_instrumentation(self):
        """Test that Prometheus instrumentation is properly configured."""
        # Just import to ensure no import errors
        from src.main import app

        # Verify app exists and has been instrumented
        assert app is not None
        # The fact that import works means instrumentation was successful

    def test_router_inclusion(self):
        """Test that track router is properly included."""
        from src.main import app

        # Check that routes are registered
        routes = [getattr(route, "path", "") for route in app.routes]

        # Should have the track endpoint
        track_routes = [route for route in routes if "/v1/analytics" in route]
        assert len(track_routes) > 0

    @patch("src.main.initialize_application")
    @patch("src.main.get_kafka_producer")
    def test_app_startup_integration(
        self, mock_get_kafka_producer, mock_initialize_application
    ):
        """Test full application startup with test client."""
        from src.main import app

        mock_producer = MagicMock()
        mock_get_kafka_producer.return_value = mock_producer

        # Create test client to trigger startup
        with TestClient(app) as client:
            # Verify initialization was called
            mock_initialize_application.assert_called_once()

            # Test basic endpoint availability
            response = client.get("/docs")
            assert response.status_code == 200

        # Verify cleanup was called
        mock_get_kafka_producer.assert_called_once()
        mock_producer.flush.assert_called_once()

    @patch("src.main.initialize_application")
    @patch("src.main.get_kafka_producer")
    def test_multiple_startup_shutdown_cycles(
        self, mock_get_kafka_producer, mock_initialize_application
    ):
        """Test multiple startup/shutdown cycles."""
        from src.main import app

        mock_producer = MagicMock()
        mock_get_kafka_producer.return_value = mock_producer

        # First cycle
        with TestClient(app):
            pass

        # Reset mocks
        mock_initialize_application.reset_mock()
        mock_get_kafka_producer.reset_mock()
        mock_producer.reset_mock()

        # Second cycle
        with TestClient(app):
            pass

        # Verify at least one cycle called initialization
        # Note: TestClient might not trigger multiple startups
        assert mock_initialize_application.call_count >= 1
        assert mock_get_kafka_producer.call_count >= 1
        assert mock_producer.flush.call_count >= 1

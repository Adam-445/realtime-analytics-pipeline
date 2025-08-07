"""Unit tests for API endpoints."""

import time

import pytest
from fastapi import status


class TestTrackEndpoint:
    """Test cases for the /track endpoint."""

    def test_track_event_success(
        self, test_client, mock_kafka_producer, sample_analytics_event
    ):
        """Test successful event tracking."""
        response = test_client.post("/v1/analytics/track", json=sample_analytics_event)

        assert response.status_code == status.HTTP_202_ACCEPTED
        assert response.json() == {"status": "accepted"}
        mock_kafka_producer.send_event.assert_called_once()

    def test_track_event_missing_required_fields(
        self, test_client, mock_kafka_producer
    ):
        """Test tracking event with missing required fields."""
        incomplete_event = {
            "event": {"type": "page_view"},
            # Missing user, device, context, metrics
        }

        response = test_client.post("/v1/analytics/track", json=incomplete_event)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        mock_kafka_producer.send_event.assert_not_called()

    def test_track_event_invalid_url(self, test_client, mock_kafka_producer):
        """Test tracking event with invalid URL in context."""
        invalid_event = {
            "event": {"type": "page_view"},
            "user": {"id": "user123"},
            "device": {
                "user_agent": "Mozilla/5.0",
                "screen_width": 1920,
                "screen_height": 1080,
            },
            "context": {"url": "not-a-valid-url", "session_id": "session123"},
            "metrics": {},
        }

        response = test_client.post("/v1/analytics/track", json=invalid_event)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        mock_kafka_producer.send_event.assert_not_called()

    def test_track_event_kafka_producer_error(
        self, test_client, mock_kafka_producer, sample_analytics_event
    ):
        """Test handling of Kafka producer errors."""
        mock_kafka_producer.send_event.side_effect = Exception(
            "Kafka connection failed"
        )

        with pytest.raises(Exception, match="Kafka connection failed"):
            test_client.post("/v1/analytics/track", json=sample_analytics_event)
        mock_kafka_producer.send_event.assert_called_once()

    def test_track_event_with_custom_properties(self, test_client, mock_kafka_producer):
        """Test tracking event with custom properties."""
        event_with_properties = {
            "event": {"type": "purchase"},
            "user": {"id": "user456"},
            "device": {
                "user_agent": "Mozilla/5.0",
                "screen_width": 1366,
                "screen_height": 768,
            },
            "context": {
                "url": "https://shop.example.com/checkout",
                "session_id": "session456",
            },
            "metrics": {"load_time": 150, "interaction_time": 5000},
            "properties": {
                "product_id": "SKU123",
                "price": 99.99,
                "currency": "USD",
                "category": "electronics",
            },
        }

        response = test_client.post("/v1/analytics/track", json=event_with_properties)

        assert response.status_code == status.HTTP_202_ACCEPTED
        assert response.json() == {"status": "accepted"}

        # Verify the event was sent to Kafka
        mock_kafka_producer.send_event.assert_called_once()
        sent_event = mock_kafka_producer.send_event.call_args[0][0]

        assert sent_event.event.type == "purchase"
        assert sent_event.user.id == "user456"
        assert sent_event.properties["product_id"] == "SKU123"
        assert sent_event.properties["price"] == 99.99

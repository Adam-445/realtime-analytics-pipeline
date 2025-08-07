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

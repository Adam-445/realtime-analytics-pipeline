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

    def test_track_event_prometheus_metrics(
        self,
        test_client,
        mock_kafka_producer,
        mock_prometheus_metrics,
        sample_analytics_event,
    ):
        """Test that Prometheus metrics are updated."""
        response = test_client.post("/v1/analytics/track", json=sample_analytics_event)

        assert response.status_code == status.HTTP_202_ACCEPTED

        # Verify metrics were called
        mock_prometheus_metrics["requests"].inc.assert_called_once()
        mock_prometheus_metrics["latency"].observe.assert_called_once()
        mock_prometheus_metrics["errors"].inc.assert_not_called()

    def test_track_event_prometheus_error_metrics(
        self,
        test_client,
        mock_kafka_producer,
        mock_prometheus_metrics,
        sample_analytics_event,
    ):
        """Test that Prometheus error metrics are updated on failure."""
        mock_kafka_producer.send_event.side_effect = Exception("Kafka error")

        with pytest.raises(Exception, match="Kafka error"):
            test_client.post("/v1/analytics/track", json=sample_analytics_event)

        # Verify error metrics were called
        mock_prometheus_metrics["requests"].inc.assert_called_once()
        mock_prometheus_metrics["errors"].inc.assert_called_once()
        mock_prometheus_metrics["latency"].observe.assert_called_once()

    def test_track_event_logging(
        self, test_client, mock_kafka_producer, mock_logger, sample_analytics_event
    ):
        """Test that events are properly logged."""
        response = test_client.post("/v1/analytics/track", json=sample_analytics_event)

        assert response.status_code == status.HTTP_202_ACCEPTED

        # Verify logging calls
        # At least request received and processed
        assert mock_logger.info.call_count >= 2

        # Check for specific log messages
        log_calls = [call.args[0] for call in mock_logger.info.call_args_list]
        assert any("Received analytics event" in msg for msg in log_calls)
        assert any("Event processed successfully" in msg for msg in log_calls)

    def test_track_event_with_ip_address(self, test_client, mock_kafka_producer):
        """Test tracking event with IP address."""
        event_with_ip = {
            "event": {"type": "page_view"},
            "user": {"id": "user789"},
            "device": {
                "user_agent": "Mozilla/5.0",
                "screen_width": 1920,
                "screen_height": 1080,
            },
            "context": {
                "url": "https://example.com/page",
                "session_id": "session789",
                "ip_address": "192.168.1.100",
                "referrer": "https://google.com",
            },
            "metrics": {"load_time": 300},
        }

        response = test_client.post("/v1/analytics/track", json=event_with_ip)

        assert response.status_code == status.HTTP_202_ACCEPTED

        # Verify the event includes IP address
        mock_kafka_producer.send_event.assert_called_once()
        sent_event = mock_kafka_producer.send_event.call_args[0][0]

        assert str(sent_event.context.ip_address) == "192.168.1.100"
        assert str(sent_event.context.referrer) == "https://google.com/"

    def test_track_event_timestamp_handling(self, test_client, mock_kafka_producer):
        """Test event timestamp handling."""
        custom_timestamp = int(time.time() * 1000) - 5000  # 5 seconds ago

        event_with_timestamp = {
            "event": {"type": "page_view"},
            "user": {"id": "user999"},
            "device": {
                "user_agent": "Mozilla/5.0",
                "screen_width": 1920,
                "screen_height": 1080,
            },
            "context": {"url": "https://example.com/page", "session_id": "session999"},
            "metrics": {},
            "timestamp": custom_timestamp,
        }

        response = test_client.post("/v1/analytics/track", json=event_with_timestamp)

        assert response.status_code == status.HTTP_202_ACCEPTED

        # Verify custom timestamp is preserved
        mock_kafka_producer.send_event.assert_called_once()
        sent_event = mock_kafka_producer.send_event.call_args[0][0]

        assert sent_event.timestamp == custom_timestamp

    def test_track_event_user_agent_variations(self, test_client, mock_kafka_producer):
        """Test different user agent strings."""
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Mozilla/5.0 (iPhone; CPU iPhone OS 14_7_1 like Mac OS X) "
            "AppleWebKit/605.1.15",
            "Custom Bot/1.0",
            "",  # Empty user agent
        ]

        for i, user_agent in enumerate(user_agents):
            event = {
                "event": {"type": "page_view"},
                "user": {"id": f"user{i}"},
                "device": {
                    "user_agent": user_agent,
                    "screen_width": 1920,
                    "screen_height": 1080,
                },
                "context": {
                    "url": "https://example.com/page",
                    "session_id": f"session{i}",
                },
                "metrics": {},
            }

            response = test_client.post("/v1/analytics/track", json=event)

            assert response.status_code == status.HTTP_202_ACCEPTED

    def test_track_event_large_properties(self, test_client, mock_kafka_producer):
        """Test event with large properties object."""
        large_properties = {f"key_{i}": f"value_{i}" for i in range(100)}

        event_with_large_props = {
            "event": {"type": "page_view"},
            "user": {"id": "user_large"},
            "device": {
                "user_agent": "Mozilla/5.0",
                "screen_width": 1920,
                "screen_height": 1080,
            },
            "context": {
                "url": "https://example.com/page",
                "session_id": "session_large",
            },
            "metrics": {},
            "properties": large_properties,
        }

        response = test_client.post("/v1/analytics/track", json=event_with_large_props)

        assert response.status_code == status.HTTP_202_ACCEPTED

        # Verify large properties are handled
        mock_kafka_producer.send_event.assert_called_once()
        sent_event = mock_kafka_producer.send_event.call_args[0][0]

        assert len(sent_event.properties) == 100
        assert sent_event.properties["key_50"] == "value_50"

    def test_track_event_content_type_validation(
        self, test_client, mock_kafka_producer
    ):
        """Test that content type validation works."""
        # Test with wrong content type
        response = test_client.post(
            "/v1/analytics/track",
            data="not json",
            headers={"Content-Type": "text/plain"},
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        mock_kafka_producer.send_event.assert_not_called()

    def test_track_event_malformed_json(self, test_client, mock_kafka_producer):
        """Test handling of malformed JSON."""
        response = test_client.post(
            "/v1/analytics/track",
            data="{invalid json}",
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        mock_kafka_producer.send_event.assert_not_called()

    def test_track_event_empty_request_body(self, test_client, mock_kafka_producer):
        """Test handling of empty request body."""
        response = test_client.post("/v1/analytics/track", json={})

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        mock_kafka_producer.send_event.assert_not_called()

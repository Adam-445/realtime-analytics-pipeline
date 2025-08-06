from unittest.mock import patch
from uuid import UUID

import pytest
from pydantic import ValidationError


def test_analytics_event_valid_creation():
    """Test that AnalyticsEvent can be created with valid data."""
    from services.ingestion.src.schemas.analytics_event import AnalyticsEvent

    # Valid event data
    event_data = {
        "event": {"type": "page_view"},
        "user": {"id": "user123"},
        "device": {
            "user_agent": "Mozilla/5.0",
            "screen_width": 1920,
            "screen_height": 1080,
        },
        "context": {"url": "https://example.com/page/", "session_id": "session123"},
        "metrics": {},
    }

    event = AnalyticsEvent(**event_data)

    # Test default values were generated
    assert event.event.id is not None
    assert isinstance(event.event.id, UUID)
    assert event.event.type == "page_view"
    assert event.user.id == "user123"
    assert event.timestamp > 0
    assert isinstance(event.timestamp, int)
    assert event.properties == {}


def test_analytics_event_with_optional_fields():
    """Test AnalyticsEvent with all optional fields populated."""
    from services.ingestion.src.schemas.analytics_event import AnalyticsEvent

    event_data = {
        "event": {"type": "click"},
        "user": {"id": "user456"},
        "device": {
            "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X)",
            "screen_width": 375,
            "screen_height": 812,
        },
        "context": {
            "url": "https://example.com/product/123/",
            "referrer": "https://google.com/",
            "ip_address": "192.168.1.1",
            "session_id": "session456",
        },
        "properties": {
            "button_text": "Add to Cart",
            "product_id": "prod123",
            "price": 29.99,
            "category_id": 5,
        },
        "metrics": {"load_time": 1200, "interaction_time": 500},
    }

    event = AnalyticsEvent(**event_data)

    assert str(event.context.referrer) == "https://google.com/"
    assert str(event.context.ip_address) == "192.168.1.1"
    assert event.properties["button_text"] == "Add to Cart"
    assert event.properties["price"] == 29.99
    assert event.properties["category_id"] == 5
    assert event.metrics.load_time == 1200
    assert event.metrics.interaction_time == 500


def test_analytics_event_invalid_url():
    """Test that invalid URLs are rejected."""
    from services.ingestion.src.schemas.analytics_event import AnalyticsEvent

    event_data = {
        "event": {"type": "page_view"},
        "user": {"id": "user123"},
        "device": {
            "user_agent": "Mozilla/5.0",
            "screen_width": 1920,
            "screen_height": 1080,
        },
        "context": {
            "url": "not-a-valid-url",  # Invalid URL
            "session_id": "session123",
        },
        "metrics": {},
    }

    with pytest.raises(ValidationError) as exc_info:
        AnalyticsEvent(**event_data)

    # Check that URL validation failed
    errors = exc_info.value.errors()
    assert any("url" in str(error).lower() for error in errors)

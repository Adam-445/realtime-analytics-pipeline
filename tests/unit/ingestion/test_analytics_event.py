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


def test_analytics_event_missing_required_fields():
    """Test that missing required fields are rejected."""
    from services.ingestion.src.schemas.analytics_event import AnalyticsEvent

    # Missing event.type
    with pytest.raises(ValidationError) as exc_info:
        AnalyticsEvent(
            **{
                "event": {},  # Missing type
                "user": {"id": "user123"},
                "device": {
                    "user_agent": "Mozilla/5.0",
                    "screen_width": 1920,
                    "screen_height": 1080,
                },
                "context": {"url": "https://example.com/", "session_id": "session123"},
                "metrics": {},
            }
        )

    errors = exc_info.value.errors()
    assert any(error["loc"] == ("event", "type") for error in errors)


def test_analytics_event_timestamp_generation():
    """Test that timestamp is automatically generated with reasonable value."""
    from services.ingestion.src.schemas.analytics_event import AnalyticsEvent

    # Mock time to test timestamp generation
    with patch("time.time", return_value=1609459200.123):  # 2021-01-01 00:00:00.123 UTC
        event_data = {
            "event": {"type": "page_view"},
            "user": {"id": "user123"},
            "device": {
                "user_agent": "Mozilla/5.0",
                "screen_width": 1920,
                "screen_height": 1080,
            },
            "context": {"url": "https://example.com", "session_id": "session123"},
            "metrics": {},
        }

        event = AnalyticsEvent(**event_data)

        # Should be 1609459200123 (epoch seconds * 1000 + milliseconds)
        assert event.timestamp == 1609459200123


def test_event_info_uuid_generation():
    """Test that EventInfo generates unique UUID v7 IDs."""
    from services.ingestion.src.schemas.analytics_event import EventInfo

    event1 = EventInfo(type="click")
    event2 = EventInfo(type="view")

    # Should be different UUIDs
    assert event1.id != event2.id
    assert isinstance(event1.id, UUID)
    assert isinstance(event2.id, UUID)

    # UUID v7 should have version 7
    assert event1.id.version == 7
    assert event2.id.version == 7


def test_device_info_validation():
    """Test DeviceInfo field validation."""
    from services.ingestion.src.schemas.analytics_event import DeviceInfo

    # Valid device info
    device = DeviceInfo(user_agent="Mozilla/5.0", screen_width=1920, screen_height=1080)
    assert device.screen_width == 1920
    assert device.screen_height == 1080

    # Test that missing required fields are caught
    with pytest.raises(ValidationError):
        DeviceInfo(
            screen_width=1920,
            screen_height=1080,
            user_agent=None,  # Invalid user_agent - should raise ValidationError
        )


def test_context_info_with_ipv6():
    """Test ContextInfo accepts IPv6 addresses."""
    from services.ingestion.src.schemas.analytics_event import ContextInfo

    context = ContextInfo(
        url="https://example.com",
        ip_address="2001:db8::1",
        session_id="session123",
        referrer=None,
    )

    assert str(context.ip_address) == "2001:db8::1"

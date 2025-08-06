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

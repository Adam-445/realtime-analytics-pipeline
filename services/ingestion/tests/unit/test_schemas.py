"""Unit tests for analytics event schemas."""

import time
from uuid import UUID

import pytest
from pydantic import ValidationError
from src.schemas.analytics_event import (
    AnalyticsEvent,
    ContextInfo,
    DeviceInfo,
    EventInfo,
    EventMetrics,
    UserInfo,
)


class TestEventInfo:
    """Test cases for EventInfo schema."""

    def test_event_info_valid(self):
        """Test valid EventInfo creation."""
        event = EventInfo(type="page_view")

        assert event.type == "page_view"
        assert isinstance(event.id, UUID)
        # UUID v7 should have version 7
        assert event.id.version == 7

    def test_event_info_missing_type(self):
        """Test EventInfo requires type field."""
        with pytest.raises(ValidationError) as exc_info:
            EventInfo()

        assert "type" in str(exc_info.value)

    def test_event_info_custom_id(self):
        """Test EventInfo with custom UUID."""
        from uuid6 import uuid7

        custom_id = uuid7()
        event = EventInfo(type="click", id=custom_id)

        assert event.id == custom_id
        assert event.type == "click"

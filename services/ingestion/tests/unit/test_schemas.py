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


class TestUserInfo:
    """Test cases for UserInfo schema."""

    def test_user_info_valid(self):
        """Test valid UserInfo creation."""
        user = UserInfo(id="user123")
        assert user.id == "user123"

    def test_user_info_missing_id(self):
        """Test UserInfo requires id field."""
        with pytest.raises(ValidationError) as exc_info:
            UserInfo()

        assert "id" in str(exc_info.value)

    def test_user_info_empty_id(self):
        """Test UserInfo with empty id."""
        user = UserInfo(id="")
        assert user.id == ""


class TestContextInfo:
    """Test cases for ContextInfo schema."""

    def test_context_info_valid(self):
        """Test valid ContextInfo creation."""
        context = ContextInfo(url="https://example.com/page", session_id="session123")

        assert str(context.url) == "https://example.com/page"
        assert context.session_id == "session123"
        assert context.referrer is None
        assert context.ip_address is None

    def test_context_info_with_referrer(self):
        """Test ContextInfo with referrer."""
        context = ContextInfo(
            url="https://example.com/page",
            referrer="https://example.com/home",
            session_id="session123",
            ip_address=None,
        )

        assert str(context.referrer) == "https://example.com/home"

    def test_context_info_with_ip_address(self):
        """Test ContextInfo with IP address."""
        context = ContextInfo(
            url="https://example.com/page",
            session_id="session123",
            referrer=None,
            ip_address="192.168.1.1",
        )

        assert str(context.ip_address) == "192.168.1.1"

    def test_context_info_invalid_url(self):
        """Test ContextInfo with invalid URL."""
        with pytest.raises(ValidationError) as exc_info:
            ContextInfo(url="not-a-url", session_id="session123")

        assert "url" in str(exc_info.value)

    def test_context_info_missing_required_fields(self):
        """Test ContextInfo missing required fields."""
        with pytest.raises(ValidationError) as exc_info:
            ContextInfo()

        error_str = str(exc_info.value)
        assert "url" in error_str
        assert "session_id" in error_str

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


class TestDeviceInfo:
    """Test cases for DeviceInfo schema."""

    def test_device_info_valid(self):
        """Test valid DeviceInfo creation."""
        device = DeviceInfo(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            screen_width=1920,
            screen_height=1080,
        )

        assert device.user_agent == "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        assert device.screen_width == 1920
        assert device.screen_height == 1080

    def test_device_info_missing_fields(self):
        """Test DeviceInfo missing required fields."""
        with pytest.raises(ValidationError) as exc_info:
            DeviceInfo()

        error_str = str(exc_info.value)
        assert "user_agent" in error_str
        assert "screen_width" in error_str
        assert "screen_height" in error_str

    def test_device_info_invalid_screen_dimensions(self):
        """Test DeviceInfo with invalid screen dimensions."""
        with pytest.raises(ValidationError):
            DeviceInfo(
                user_agent="Mozilla/5.0",
                screen_width="not_a_number",
                screen_height=1080,
            )


class TestEventMetrics:
    """Test cases for EventMetrics schema."""

    def test_event_metrics_valid(self):
        """Test valid EventMetrics creation."""
        metrics = EventMetrics(load_time=250, interaction_time=1500)

        assert metrics.load_time == 250
        assert metrics.interaction_time == 1500

    def test_event_metrics_optional_fields(self):
        """Test EventMetrics with optional fields."""
        metrics = EventMetrics()

        assert metrics.load_time is None
        assert metrics.interaction_time is None

    def test_event_metrics_partial_fields(self):
        """Test EventMetrics with some fields."""
        metrics = EventMetrics(load_time=300)

        assert metrics.load_time == 300
        assert metrics.interaction_time is None


class TestAnalyticsEvent:
    """Test cases for AnalyticsEvent schema."""

    def test_analytics_event_valid(self):
        """Test valid AnalyticsEvent creation."""
        event_data = {
            "event": {"type": "page_view"},
            "user": {"id": "user123"},
            "device": {
                "user_agent": "Mozilla/5.0",
                "screen_width": 1920,
                "screen_height": 1080,
            },
            "context": {"url": "https://example.com/page", "session_id": "session123"},
            "metrics": {"load_time": 250},
        }

        event = AnalyticsEvent(**event_data)

        assert event.event.type == "page_view"
        assert event.user.id == "user123"
        assert event.device.screen_width == 1920
        assert str(event.context.url) == "https://example.com/page"
        assert event.metrics.load_time == 250
        assert isinstance(event.timestamp, int)
        assert event.properties == {}

    def test_analytics_event_with_properties(self):
        """Test AnalyticsEvent with custom properties."""
        event_data = {
            "event": {"type": "click"},
            "user": {"id": "user456"},
            "device": {
                "user_agent": "Mozilla/5.0",
                "screen_width": 1280,
                "screen_height": 720,
            },
            "context": {
                "url": "https://example.com/button",
                "session_id": "session456",
            },
            "metrics": {},
            "properties": {
                "button_text": "Sign Up",
                "position_x": 100,
                "position_y": 200,
                "conversion_value": 99.99,
            },
        }

        event = AnalyticsEvent(**event_data)

        assert event.properties["button_text"] == "Sign Up"
        assert event.properties["position_x"] == 100
        assert event.properties["conversion_value"] == 99.99

    def test_analytics_event_custom_timestamp(self):
        """Test AnalyticsEvent with custom timestamp."""
        custom_timestamp = int(time.time() * 1000) - 10000

        event_data = {
            "event": {"type": "page_view"},
            "user": {"id": "user123"},
            "device": {
                "user_agent": "Mozilla/5.0",
                "screen_width": 1920,
                "screen_height": 1080,
            },
            "context": {"url": "https://example.com/page", "session_id": "session123"},
            "metrics": {},
            "timestamp": custom_timestamp,
        }

        event = AnalyticsEvent(**event_data)
        assert event.timestamp == custom_timestamp

    def test_analytics_event_missing_required_fields(self):
        """Test AnalyticsEvent missing required fields."""
        with pytest.raises(ValidationError) as exc_info:
            AnalyticsEvent()

        error_str = str(exc_info.value)
        assert "event" in error_str
        assert "user" in error_str
        assert "device" in error_str
        assert "context" in error_str
        assert "metrics" in error_str

    def test_analytics_event_json_serialization(self):
        """Test AnalyticsEvent JSON serialization."""
        event_data = {
            "event": {"type": "page_view"},
            "user": {"id": "user123"},
            "device": {
                "user_agent": "Mozilla/5.0",
                "screen_width": 1920,
                "screen_height": 1080,
            },
            "context": {"url": "https://example.com/page", "session_id": "session123"},
            "metrics": {"load_time": 250},
        }

        event = AnalyticsEvent(**event_data)
        json_str = event.model_dump_json()

        assert isinstance(json_str, str)
        assert "page_view" in json_str
        assert "user123" in json_str
        assert "session123" in json_str

    def test_analytics_event_model_dump(self):
        """Test AnalyticsEvent model dump."""
        event_data = {
            "event": {"type": "click"},
            "user": {"id": "user789"},
            "device": {
                "user_agent": "Mozilla/5.0",
                "screen_width": 1366,
                "screen_height": 768,
            },
            "context": {"url": "https://example.com/form", "session_id": "session789"},
            "metrics": {"interaction_time": 2000},
        }

        event = AnalyticsEvent(**event_data)
        dumped = event.model_dump()

        assert isinstance(dumped, dict)
        assert dumped["event"]["type"] == "click"
        assert dumped["user"]["id"] == "user789"
        assert "timestamp" in dumped

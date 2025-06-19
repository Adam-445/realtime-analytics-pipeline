import time

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, IPvAnyAddress
from uuid6 import UUID, uuid7


class EventInfo(BaseModel):
    id: UUID = Field(default_factory=uuid7, description="UUID v7 (time-based)")
    type: str = Field(..., description="Core event category")

    model_config = ConfigDict(arbitrary_types_allowed=True)


class UserInfo(BaseModel):
    id: str = Field(..., description="The user identifier")


class ContextInfo(BaseModel):
    url: HttpUrl = Field(..., description="Current page URL")
    referrer: HttpUrl | None = Field(None, description="Previous page URL")
    ip_address: IPvAnyAddress | None = Field(
        None, description="IP address (Optional, for geo-lookup)"
    )
    session_id: str = Field(..., description="Stickiness across tabs/sessions")


class DeviceInfo(BaseModel):
    user_agent: str = Field(..., description="Browser or device user-agent string")
    screen_width: int
    screen_height: int


class EventMetrics(BaseModel):
    load_time: int | None = Field(None, description="Page load time (ms)")
    interaction_time: int | None = Field(None, description="User interaction time (ms)")


class AnalyticsEvent(BaseModel):
    event: EventInfo
    user: UserInfo
    context: ContextInfo
    properties: dict[str, str | int | float] = Field(
        default_factory=dict, description="Custom metadata key/value pairs"
    )
    metrics: EventMetrics
    timestamp: int = Field(
        default_factory=lambda: int(time.time() * 1000),
        description="Epoch-ms when the event occured",
    )

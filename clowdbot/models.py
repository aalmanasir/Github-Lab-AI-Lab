"""Pydantic models for API requests, responses, and data records."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

__all__ = [
    "EventRecord",
    "CommandRecord",
    "WebhookRecord",
    "UptimeRecord",
    "StatusResponse",
    "EventFilter",
    "TriggerRequest",
    "HealthResponse",
    "APIResponse",
]


class EventRecord(BaseModel):
    """Represents an event log entry."""
    id: int
    timestamp: str
    source: str
    event_type: str
    severity: str = "info"
    summary: str
    detail: str | None = None
    metadata: Any | None = None
    created_at: str | None = None


class CommandRecord(BaseModel):
    """Represents a command log entry."""
    id: int
    timestamp: str
    user_id: str | None = None
    username: str | None = None
    command: str
    args: str | None = None
    channel: str | None = None
    response: str | None = None
    created_at: str | None = None


class WebhookRecord(BaseModel):
    """Represents a webhook log entry."""
    id: int
    timestamp: str
    provider: str
    event_type: str
    delivery_id: str | None = None
    payload: str | None = None
    processed: bool = False
    created_at: str | None = None


class UptimeRecord(BaseModel):
    """Represents an uptime check entry."""
    id: int
    timestamp: str
    status: str
    response_time_ms: float | None = None
    endpoint: str | None = None
    created_at: str | None = None


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    timestamp: str
    version: str
    checks: dict[str, bool] = Field(default_factory=dict)


class StatusResponse(BaseModel):
    """System status dashboard response."""
    uptime_seconds: float
    environment: str
    version: str
    event_stats: dict[str, Any] = Field(default_factory=dict)
    recent_events: list[EventRecord] = Field(default_factory=list)
    bot_connected: bool = False
    system_info: dict[str, Any] = Field(default_factory=dict)


class EventFilter(BaseModel):
    """Query parameters for event filtering."""
    source: str | None = None
    event_type: str | None = None
    severity: str | None = None
    since: str | None = None
    until: str | None = None
    limit: int = Field(default=50, ge=1, le=200)
    offset: int = Field(default=0, ge=0)


class TriggerRequest(BaseModel):
    """Request body for manual trigger endpoints."""
    source: str = "manual"
    event_type: str = "manual"
    severity: str = "info"
    summary: str = ""
    detail: str | None = None
    metadata: dict[str, Any] | None = None


class APIResponse(BaseModel):
    """Standard API response envelope."""
    status: str = "ok"
    data: Any | None = None
    error: str | None = None
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

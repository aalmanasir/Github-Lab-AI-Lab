"""Tests for events API endpoints."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from clowdbot.database import log_event


@pytest.mark.asyncio
async def test_list_events_empty(client: AsyncClient) -> None:
    """Test GET /api/events returns empty list when no events."""
    resp = await client.get("/api/events")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["data"]["events"] == []
    assert data["data"]["count"] == 0


@pytest.mark.asyncio
async def test_create_and_list_events(client: AsyncClient) -> None:
    """Test creating events and listing them."""
    event_id = await log_event(
        source="test",
        event_type="test_event",
        summary="Test event summary",
        severity="info",
        detail="Some detail",
    )
    assert event_id > 0

    resp = await client.get("/api/events")
    assert resp.status_code == 200
    data = resp.json()
    assert data["data"]["count"] >= 1
    assert any(e["summary"] == "Test event summary" for e in data["data"]["events"])


@pytest.mark.asyncio
async def test_get_event_by_id(client: AsyncClient) -> None:
    """Test GET /api/events/{id} returns correct event."""
    event_id = await log_event(
        source="test",
        event_type="detail_test",
        summary="Detail test event",
        severity="warning",
    )

    resp = await client.get(f"/api/events/{event_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["data"]["id"] == event_id
    assert data["data"]["severity"] == "warning"


@pytest.mark.asyncio
async def test_get_event_not_found(client: AsyncClient) -> None:
    """Test GET /api/events/{id} for non-existent event."""
    resp = await client.get("/api/events/99999")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "error"


@pytest.mark.asyncio
async def test_event_stats(client: AsyncClient) -> None:
    """Test GET /api/events/stats returns statistics."""
    await log_event(source="test", event_type="stat_test", summary="Stats test", severity="error")

    resp = await client.get("/api/events/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "total_events" in data["data"]


@pytest.mark.asyncio
async def test_filter_events_by_severity(client: AsyncClient) -> None:
    """Test filtering events by severity."""
    await log_event(source="test", event_type="filter_test", summary="Critical event", severity="critical")
    await log_event(source="test", event_type="filter_test", summary="Info event", severity="info")

    resp = await client.get("/api/events?severity=critical")
    assert resp.status_code == 200
    data = resp.json()
    for event in data["data"]["events"]:
        assert event["severity"] == "critical"


@pytest.mark.asyncio
async def test_trigger_event(client: AsyncClient) -> None:
    """Test POST /api/trigger/event creates an event."""
    resp = await client.post(
        "/api/trigger/event",
        json={"source": "test", "summary": "Triggered event", "severity": "info"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "event_id" in data["data"]

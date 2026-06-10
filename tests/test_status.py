"""Tests for status endpoint."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_status_endpoint(client: AsyncClient) -> None:
    """Test GET /api/status returns expected structure."""
    resp = await client.get("/api/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"

    status_data = data["data"]
    assert "uptime_seconds" in status_data
    assert "environment" in status_data
    assert "version" in status_data
    assert "event_stats" in status_data
    assert "recent_events" in status_data
    assert "system_info" in status_data
    assert isinstance(status_data["uptime_seconds"], (int, float))
    assert status_data["uptime_seconds"] >= 0


@pytest.mark.asyncio
async def test_status_system_info(client: AsyncClient) -> None:
    """Test GET /api/status system_info contains expected fields."""
    resp = await client.get("/api/status")
    data = resp.json()
    sys_info = data["data"]["system_info"]
    assert "python" in sys_info
    assert "platform" in sys_info
    assert "hostname" in sys_info


@pytest.mark.asyncio
async def test_status_event_stats(client: AsyncClient) -> None:
    """Test GET /api/status event_stats has expected keys."""
    resp = await client.get("/api/status")
    data = resp.json()
    stats = data["data"]["event_stats"]
    assert "total_events" in stats
    assert "last_24h" in stats
    assert "by_severity" in stats
    assert "by_source" in stats

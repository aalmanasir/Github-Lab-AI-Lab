"""Tests for trigger endpoints."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_trigger_health_check(client: AsyncClient) -> None:
    """Test POST /api/trigger/health-check runs health checks."""
    resp = await client.post("/api/trigger/health-check")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["data"] is not None


@pytest.mark.asyncio
async def test_trigger_event_basic(client: AsyncClient) -> None:
    """Test POST /api/trigger/event with minimal payload."""
    resp = await client.post(
        "/api/trigger/event",
        json={"summary": "Test trigger event"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "event_id" in data["data"]


@pytest.mark.asyncio
async def test_trigger_event_full_payload(client: AsyncClient) -> None:
    """Test POST /api/trigger/event with full payload."""
    resp = await client.post(
        "/api/trigger/event",
        json={
            "source": "ci",
            "event_type": "deployment",
            "severity": "warning",
            "summary": "Deployment started",
            "detail": "Deploying v1.2.3 to production",
            "metadata": {"version": "1.2.3", "env": "production"},
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["data"]["event_id"] > 0


@pytest.mark.asyncio
async def test_trigger_event_empty_body(client: AsyncClient) -> None:
    """Test POST /api/trigger/event with empty body uses defaults."""
    resp = await client.post("/api/trigger/event", json={})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"


@pytest.mark.asyncio
async def test_trigger_alert_test(client: AsyncClient) -> None:
    """Test POST /api/trigger/alert-test runs the alert pipeline."""
    resp = await client.post("/api/trigger/alert-test")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "alert_sent" in data["data"]

"""Tests for health endpoints."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_endpoint(client: AsyncClient) -> None:
    """Test GET /health returns healthy status."""
    resp = await client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["data"]["status"] == "healthy"
    assert "version" in data["data"]
    assert "timestamp" in data["data"]


@pytest.mark.asyncio
async def test_ready_endpoint(client: AsyncClient) -> None:
    """Test GET /ready checks database connectivity."""
    resp = await client.get("/ready")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["data"]["ready"] is True
    assert data["data"]["database"] == "connected"

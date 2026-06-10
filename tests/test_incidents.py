"""Tests for incident response system."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from clowdbot.incidents.classifier import classify_incident
from clowdbot.incidents.recommender import get_recommendations


def test_classify_outage() -> None:
    result = classify_incident("Production API is down", "All endpoints returning 502")
    assert result["incident_type"] == "outage"
    assert result["severity"] == "critical"
    assert result["confidence"] > 0.5

def test_classify_security() -> None:
    result = classify_incident("Unauthorized access detected", "CVE-2024-1234 exploitation attempt")
    assert result["incident_type"] == "security"
    assert result["severity"] == "critical"

def test_classify_performance() -> None:
    result = classify_incident("API latency spike", "Response times degraded to 5s")
    assert result["incident_type"] == "performance"
    assert result["severity"] == "high"

def test_classify_deployment() -> None:
    result = classify_incident("Deploy failed", "Build failure on main branch")
    assert result["incident_type"] == "deployment"

def test_classify_unknown() -> None:
    result = classify_incident("Something happened", "Not sure what")
    assert result["incident_type"] == "unknown"
    assert result["confidence"] < 0.5

def test_recommendations_outage() -> None:
    rec = get_recommendations("outage", "critical", "API down")
    assert "immediate_actions" in rec["playbook"]
    assert len(rec["playbook"]["immediate_actions"]) > 0
    assert rec["severity_response"]["requires_war_room"] is True
    assert "recommendation_text" in rec

def test_recommendations_default() -> None:
    rec = get_recommendations("unknown_type", "medium", "Something broke")
    assert "immediate_actions" in rec["playbook"]
    assert rec["severity_response"]["requires_war_room"] is False

@pytest.mark.asyncio
async def test_create_incident_api(client: AsyncClient) -> None:
    resp = await client.post("/api/incidents", json={
        "title": "Test outage incident",
        "description": "The main API is returning 503 errors",
        "source": "test",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "incident" in data["data"]
    assert "classification" in data["data"]
    assert "recommendations" in data["data"]
    assert data["data"]["classification"]["incident_type"] == "outage"

@pytest.mark.asyncio
async def test_list_incidents_api(client: AsyncClient) -> None:
    await client.post("/api/incidents", json={"title": "Test incident for listing"})
    resp = await client.get("/api/incidents")
    assert resp.status_code == 200
    data = resp.json()
    assert data["data"]["count"] >= 1

@pytest.mark.asyncio
async def test_get_incident_api(client: AsyncClient) -> None:
    create_resp = await client.post("/api/incidents", json={"title": "Detailed test incident"})
    incident_id = create_resp.json()["data"]["incident"]["id"]
    resp = await client.get(f"/api/incidents/{incident_id}")
    assert resp.status_code == 200
    assert resp.json()["data"]["id"] == incident_id

@pytest.mark.asyncio
async def test_resolve_incident_api(client: AsyncClient) -> None:
    create_resp = await client.post("/api/incidents", json={"title": "Incident to resolve"})
    incident_id = create_resp.json()["data"]["incident"]["id"]
    resp = await client.post(f"/api/incidents/{incident_id}/resolve", json={
        "resolution": "Fixed the config",
        "resolved_by": "test-user",
    })
    assert resp.status_code == 200
    assert resp.json()["data"]["status"] == "resolved"

@pytest.mark.asyncio
async def test_update_incident_api(client: AsyncClient) -> None:
    create_resp = await client.post("/api/incidents", json={"title": "Incident to update"})
    incident_id = create_resp.json()["data"]["incident"]["id"]
    resp = await client.patch(f"/api/incidents/{incident_id}", json={
        "severity": "critical",
        "status": "investigating",
    })
    assert resp.status_code == 200
    assert resp.json()["data"]["severity"] == "critical"

@pytest.mark.asyncio
async def test_incident_stats_api(client: AsyncClient) -> None:
    await client.post("/api/incidents", json={"title": "Stats test incident"})
    resp = await client.get("/api/incidents/stats")
    assert resp.status_code == 200
    assert "by_status" in resp.json()["data"]

@pytest.mark.asyncio
async def test_incident_not_found(client: AsyncClient) -> None:
    resp = await client.get("/api/incidents/99999")
    assert resp.status_code == 200
    assert resp.json()["status"] == "error"

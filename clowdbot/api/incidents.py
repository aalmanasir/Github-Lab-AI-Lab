"""Incident management API endpoints."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from clowdbot.incidents.service import IncidentService
from clowdbot.models import APIResponse

__all__ = ["router"]

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/incidents", tags=["incidents"])


class CreateIncidentRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    description: str | None = Field(None, max_length=5000)
    source: str = Field(default="api", max_length=100)
    severity: str | None = Field(None, pattern="^(critical|high|medium|low|info)$")
    incident_type: str | None = Field(None, max_length=100)
    metadata: dict[str, Any] | None = None
    use_ai: bool = False


class UpdateIncidentRequest(BaseModel):
    title: str | None = Field(None, max_length=500)
    description: str | None = Field(None, max_length=5000)
    severity: str | None = Field(None, pattern="^(critical|high|medium|low|info)$")
    status: str | None = Field(None, pattern="^(open|investigating|mitigating|resolved|closed)$")
    assigned_to: str | None = Field(None, max_length=200)


class ResolveIncidentRequest(BaseModel):
    resolution: str = Field(..., min_length=1, max_length=5000)
    resolved_by: str = Field(..., min_length=1, max_length=200)


@router.post("")
async def create_incident(req: CreateIncidentRequest) -> APIResponse:
    """Create a new incident with automatic classification and recommendations."""
    result = await IncidentService.create(
        title=req.title,
        description=req.description,
        source=req.source,
        severity=req.severity,
        incident_type=req.incident_type,
        metadata=req.metadata,
        use_ai=req.use_ai,
    )
    return APIResponse(status="ok", data=result)


@router.get("")
async def list_incidents(
    status: str | None = Query(None),
    severity: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> APIResponse:
    """List incidents with optional filters."""
    incidents = await IncidentService.list_all(
        status=status, severity=severity, limit=limit, offset=offset,
    )
    return APIResponse(status="ok", data={"incidents": incidents, "count": len(incidents)})


@router.get("/stats")
async def incident_stats() -> APIResponse:
    """Get incident statistics."""
    stats = await IncidentService.stats()
    return APIResponse(status="ok", data=stats)


@router.get("/{incident_id}")
async def get_incident(incident_id: int) -> APIResponse:
    """Get incident by ID with full details."""
    incident = await IncidentService.get(incident_id)
    if incident is None:
        return APIResponse(status="error", error=f"Incident {incident_id} not found")
    return APIResponse(status="ok", data=incident)


@router.patch("/{incident_id}")
async def update_incident(incident_id: int, req: UpdateIncidentRequest) -> APIResponse:
    """Update incident fields."""
    fields = {k: v for k, v in req.model_dump().items() if v is not None}
    if not fields:
        return APIResponse(status="error", error="No fields to update")
    success = await IncidentService.update(incident_id, **fields)
    if not success:
        return APIResponse(status="error", error=f"Incident {incident_id} not found or update failed")
    incident = await IncidentService.get(incident_id)
    return APIResponse(status="ok", data=incident)


@router.post("/{incident_id}/resolve")
async def resolve_incident(incident_id: int, req: ResolveIncidentRequest) -> APIResponse:
    """Resolve an incident."""
    success = await IncidentService.resolve(incident_id, req.resolution, req.resolved_by)
    if not success:
        return APIResponse(status="error", error=f"Incident {incident_id} not found or already resolved")
    incident = await IncidentService.get(incident_id)
    return APIResponse(status="ok", data=incident)

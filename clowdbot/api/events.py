"""Event history and querying endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Query

from clowdbot.database import get_event_by_id, get_event_stats, get_events, search_events
from clowdbot.models import APIResponse

__all__ = ["router"]

router = APIRouter(prefix="/events", tags=["events"])


@router.get("")
async def list_events(
    source: str | None = Query(None),
    event_type: str | None = Query(None, alias="type"),
    severity: str | None = Query(None),
    since: str | None = Query(None),
    until: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> APIResponse:
    """Get paginated event history with optional filters."""
    events = await get_events(
        source=source,
        event_type=event_type,
        severity=severity,
        since=since,
        until=until,
        limit=limit,
        offset=offset,
    )
    return APIResponse(status="ok", data={"events": events, "count": len(events), "limit": limit, "offset": offset})


@router.get("/stats")
async def event_stats() -> APIResponse:
    """Get aggregate event statistics."""
    stats = await get_event_stats()
    return APIResponse(status="ok", data=stats)


@router.get("/search")
async def search(q: str = Query(..., min_length=1), limit: int = Query(20, ge=1, le=100)) -> APIResponse:
    """Search events by summary or detail text."""
    results = await search_events(q, limit=limit)
    return APIResponse(status="ok", data={"events": results, "count": len(results), "query": q})


@router.get("/{event_id}")
async def get_event(event_id: int) -> APIResponse:
    """Get a single event by ID."""
    event = await get_event_by_id(event_id)
    if event is None:
        return APIResponse(status="error", error=f"Event {event_id} not found")
    return APIResponse(status="ok", data=event)

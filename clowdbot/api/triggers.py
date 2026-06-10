"""Manual trigger endpoints for health checks, alerts, and events."""

from __future__ import annotations

import logging

from fastapi import APIRouter

from clowdbot.database import log_event
from clowdbot.models import APIResponse, TriggerRequest
from clowdbot.monitoring.alerts import send_alert
from clowdbot.monitoring.health import run_health_checks

__all__ = ["router"]

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/trigger", tags=["triggers"])


@router.post("/health-check")
async def trigger_health_check() -> APIResponse:
    """Manually trigger a health check."""
    logger.info("Manual health check triggered")
    results = await run_health_checks()
    await log_event(
        source="api",
        event_type="health_check",
        summary="Manual health check triggered",
        severity="info",
        metadata=results,
    )
    return APIResponse(status="ok", data=results)


@router.post("/alert-test")
async def trigger_alert_test() -> APIResponse:
    """Test the alert pipeline."""
    logger.info("Alert test triggered")
    success = await send_alert(
        title="🧪 Alert Test",
        message="This is a test alert from ClowdBot.",
        severity="info",
    )
    await log_event(
        source="api",
        event_type="alert_test",
        summary="Alert test triggered",
        severity="info",
        metadata={"delivered": success},
    )
    return APIResponse(status="ok", data={"alert_sent": success})


@router.post("/event")
async def trigger_event(req: TriggerRequest) -> APIResponse:
    """Inject a manual event into the event log."""
    logger.info("Manual event injection: %s", req.summary)
    event_id = await log_event(
        source=req.source,
        event_type=req.event_type,
        summary=req.summary or "Manual event",
        severity=req.severity,
        detail=req.detail,
        metadata=req.metadata,
    )
    return APIResponse(status="ok", data={"event_id": event_id})

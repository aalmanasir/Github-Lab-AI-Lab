"""Health and readiness endpoints."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter

from clowdbot.config import get_settings
from clowdbot.database import check_db_health
from clowdbot.models import APIResponse, HealthResponse

__all__ = ["router"]

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> APIResponse:
    """Basic health check endpoint."""
    settings = get_settings()
    return APIResponse(
        status="ok",
        data=HealthResponse(
            status="healthy",
            timestamp=datetime.now(timezone.utc).isoformat(),
            version=settings.APP_VERSION,
        ).model_dump(),
    )


@router.get("/ready")
async def ready() -> APIResponse:
    """Readiness check - verifies DB connectivity."""
    db_ok = await check_db_health()
    if db_ok:
        return APIResponse(
            status="ok",
            data={"ready": True, "database": "connected"},
        )
    return APIResponse(
        status="error",
        error="Database not ready",
        data={"ready": False, "database": "disconnected"},
    )

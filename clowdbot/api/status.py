"""Status dashboard endpoint."""

from __future__ import annotations

import platform
import time
from typing import Any

from fastapi import APIRouter

from clowdbot.config import get_settings
from clowdbot.database import get_event_stats, get_recent_events
from clowdbot.models import APIResponse

__all__ = ["router"]

router = APIRouter(tags=["status"])

_start_time = time.time()


@router.get("/status")
async def get_status() -> APIResponse:
    """Dashboard status: uptime, events, bot status, system info."""
    settings = get_settings()
    stats = await get_event_stats()
    recent = await get_recent_events(limit=5)

    data: dict[str, Any] = {
        "uptime_seconds": round(time.time() - _start_time, 2),
        "environment": settings.ENVIRONMENT,
        "version": settings.APP_VERSION,
        "event_stats": stats,
        "recent_events": recent,
        "bot_connected": False,  # Updated by bot lifecycle
        "system_info": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "hostname": platform.node(),
        },
    }
    return APIResponse(status="ok", data=data)

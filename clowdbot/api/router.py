"""Main API router - mounts all sub-routers."""

from __future__ import annotations

from fastapi import APIRouter

from clowdbot.api.events import router as events_router
from clowdbot.api.health import router as health_router
from clowdbot.api.incidents import router as incidents_router
from clowdbot.api.status import router as status_router
from clowdbot.api.triggers import router as triggers_router

__all__ = ["api_router", "health_router"]

api_router = APIRouter(prefix="/api")
api_router.include_router(status_router)
api_router.include_router(events_router)
api_router.include_router(triggers_router)
api_router.include_router(incidents_router)

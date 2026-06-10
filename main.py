"""ClowdBot entrypoint - starts FastAPI server and Discord bot concurrently."""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from clowdbot.api.health import router as health_router
from clowdbot.api.middleware import setup_middleware
from clowdbot.api.router import api_router
from clowdbot.bot.client import create_bot, start_bot
from clowdbot.bot.commands import setup_commands
from clowdbot.config import get_settings
from clowdbot.database import close_db, init_db
from clowdbot.logging_config import setup_logging
from clowdbot.monitoring.uptime import start_uptime_monitor, stop_uptime_monitor
from clowdbot.webhooks.github import router as github_router

logger = logging.getLogger(__name__)

_bot_task: asyncio.Task | None = None  # type: ignore[type-arg]
_uptime_task: asyncio.Task | None = None  # type: ignore[type-arg]


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler for startup and shutdown."""
    global _bot_task, _uptime_task

    settings = get_settings()
    setup_logging(settings.LOG_LEVEL)
    logger.info("Starting ClowdBot v%s (%s)", settings.APP_VERSION, settings.ENVIRONMENT)

    # Initialize database
    await init_db()
    logger.info("Database initialized")

    # Create and start Discord bot
    bot = create_bot()
    setup_commands(bot)
    _bot_task = asyncio.create_task(start_bot(bot))

    # Start uptime monitor
    _uptime_task = asyncio.create_task(start_uptime_monitor())

    logger.info("ClowdBot startup complete")
    yield

    # Shutdown
    logger.info("Shutting down ClowdBot...")
    stop_uptime_monitor()

    if _uptime_task and not _uptime_task.done():
        _uptime_task.cancel()
        try:
            await _uptime_task
        except asyncio.CancelledError:
            pass

    if _bot_task and not _bot_task.done():
        from clowdbot.bot.client import bot_instance
        if bot_instance and not bot_instance.is_closed():
            await bot_instance.close()
        _bot_task.cancel()
        try:
            await _bot_task
        except asyncio.CancelledError:
            pass

    await close_db()
    logger.info("ClowdBot shutdown complete")


def create_app() -> FastAPI:
    """Create the FastAPI application with all routes mounted."""
    settings = get_settings()

    app = FastAPI(
        title="ClowdBot",
        description="Autonomous Operations Agent - Discord bot + REST API + webhook handler for infrastructure monitoring and event management.",
        version=settings.APP_VERSION,
        lifespan=lifespan,
        contact={"name": "ClowdBot", "url": "https://github.com/clowdops/clowdbot-agent"},
        license_info={"name": "MIT", "url": "https://opensource.org/licenses/MIT"},
        openapi_tags=[
            {"name": "health", "description": "Health and readiness probes"},
            {"name": "status", "description": "System status dashboard"},
            {"name": "events", "description": "Event log queries and search"},
            {"name": "triggers", "description": "Manual trigger endpoints"},
            {"name": "webhooks", "description": "Incoming webhook handlers"},
        ],
    )

    # Mount routers
    app.include_router(health_router)
    app.include_router(api_router)
    app.include_router(github_router)

    # Setup middleware (CORS, rate limiting, request logging)
    setup_middleware(app)

    # Global exception handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=500,
            content={"status": "error", "error": "Internal server error"},
        )

    return app


app = create_app()


def main() -> None:
    """Main entrypoint - run the application."""
    settings = get_settings()
    uvicorn.run(
        "main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        log_level=settings.LOG_LEVEL.lower(),
        reload=settings.ENVIRONMENT == "development",
    )


if __name__ == "__main__":
    main()

"""Uptime tracking - periodic self-check and logging."""

from __future__ import annotations

import asyncio
import logging
import time

import aiohttp

from clowdbot.config import get_settings
from clowdbot.database import log_uptime

__all__ = ["start_uptime_monitor", "get_uptime_summary"]

logger = logging.getLogger(__name__)

_running = False


async def _check_self() -> tuple[str, float]:
    """Perform a self-health check against the local API.

    Returns:
        Tuple of (status, response_time_ms).
    """
    settings = get_settings()
    url = f"http://127.0.0.1:{settings.API_PORT}/health"
    start = time.monotonic()
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                elapsed = (time.monotonic() - start) * 1000
                if resp.status == 200:
                    return "healthy", round(elapsed, 2)
                return "degraded", round(elapsed, 2)
    except aiohttp.ClientError:
        elapsed = (time.monotonic() - start) * 1000
        return "unhealthy", round(elapsed, 2)
    except Exception:
        elapsed = (time.monotonic() - start) * 1000
        logger.exception("Uptime check error")
        return "error", round(elapsed, 2)


async def start_uptime_monitor(interval_seconds: int = 300) -> None:
    """Start the periodic uptime monitoring loop.

    Args:
        interval_seconds: Check interval in seconds (default 5 minutes).
    """
    global _running
    _running = True
    # Resolve settings once – they are immutable after startup.
    settings = get_settings()
    endpoint = f"http://127.0.0.1:{settings.API_PORT}/health"
    logger.info("Uptime monitor started (interval: %ds)", interval_seconds)

    # Wait a bit for API to be ready
    await asyncio.sleep(10)

    while _running:
        try:
            status, response_time = await _check_self()
            await log_uptime(
                status=status,
                response_time_ms=response_time,
                endpoint=endpoint,
            )
            if status != "healthy":
                logger.warning("Uptime check: %s (%.2fms)", status, response_time)
        except Exception:
            logger.exception("Uptime monitor iteration error")

        await asyncio.sleep(interval_seconds)


def stop_uptime_monitor() -> None:
    """Stop the uptime monitoring loop."""
    global _running
    _running = False
    logger.info("Uptime monitor stopped")


async def get_uptime_summary() -> dict:
    """Get a summary of recent uptime data."""
    from clowdbot.database import get_db

    try:
        db = await get_db()
        cursor = await db.execute(
            "SELECT COUNT(*) as total, "
            "SUM(CASE WHEN status = 'healthy' THEN 1 ELSE 0 END) as healthy, "
            "AVG(response_time_ms) as avg_response "
            "FROM uptime_log WHERE timestamp >= datetime('now', '-24 hours')"
        )
        row = await cursor.fetchone()
        if row:
            total = row["total"] or 0
            healthy_count = row["healthy"] or 0
            return {
                "total_checks": total,
                "healthy_checks": healthy_count,
                "uptime_pct": round((healthy_count / total * 100), 2) if total > 0 else 100.0,
                "avg_response_ms": round(row["avg_response"] or 0, 2),
            }
    except Exception:
        logger.exception("Failed to get uptime summary")
    return {"total_checks": 0, "healthy_checks": 0, "uptime_pct": 100.0, "avg_response_ms": 0.0}

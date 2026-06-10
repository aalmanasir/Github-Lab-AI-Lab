"""Internal health check logic."""

from __future__ import annotations

import logging
from typing import Any

from clowdbot.bot.client import is_bot_connected
from clowdbot.database import check_db_health

__all__ = ["run_health_checks"]

logger = logging.getLogger(__name__)


async def run_health_checks() -> dict[str, Any]:
    """Run all internal health checks and return composite results.

    Returns:
        Dict with 'healthy' bool and 'checks' dict of individual results.
    """
    checks: dict[str, bool] = {}

    # Database check
    try:
        checks["database"] = await check_db_health()
    except Exception:
        logger.exception("Database health check error")
        checks["database"] = False

    # Discord bot check
    checks["discord_bot"] = is_bot_connected()

    # API check (self — always true if we're running)
    checks["api"] = True

    healthy = all(v for k, v in checks.items() if k != "discord_bot")  # Bot is optional
    logger.info("Health check results: healthy=%s, checks=%s", healthy, checks)

    return {"healthy": healthy, "checks": checks}

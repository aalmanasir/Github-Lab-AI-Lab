"""Alerting scaffolding - webhook-based alert delivery."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

import aiohttp

from clowdbot.config import get_settings

__all__ = ["send_alert"]

logger = logging.getLogger(__name__)

SEVERITY_COLORS = {
    "info": 0x3498DB,
    "warning": 0xF39C12,
    "error": 0xE74C3C,
    "critical": 0x8B0000,
}


async def send_alert(
    title: str,
    message: str,
    severity: str = "info",
    fields: list[dict[str, str]] | None = None,
) -> bool:
    """Send an alert to the configured webhook URL (Discord/Slack format).

    Args:
        title: Alert title.
        message: Alert body message.
        severity: Severity level (info, warning, error, critical).
        fields: Optional list of {"name": ..., "value": ...} fields.

    Returns:
        True if alert was delivered, False otherwise.
    """
    settings = get_settings()
    if not settings.ALERT_WEBHOOK_URL:
        logger.warning("No ALERT_WEBHOOK_URL configured - alert not sent: %s", title)
        return False

    color = SEVERITY_COLORS.get(severity, 0x95A5A6)
    embed: dict[str, Any] = {
        "title": title,
        "description": message,
        "color": color,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "footer": {"text": f"ClowdBot | {settings.ENVIRONMENT}"},
    }

    if fields:
        embed["fields"] = [{"name": f["name"], "value": f["value"], "inline": True} for f in fields]

    payload = {"embeds": [embed]}

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                settings.ALERT_WEBHOOK_URL,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status in (200, 204):
                    logger.info("Alert delivered: %s", title)
                    return True
                body = await resp.text()
                logger.error("Alert delivery failed (HTTP %d): %s", resp.status, body[:200])
                return False
    except aiohttp.ClientError as e:
        logger.error("Alert delivery network error: %s", e)
        return False
    except Exception:
        logger.exception("Unexpected error sending alert")
        return False

"""Discord bot commands."""

from __future__ import annotations

import json
import logging
import platform
import time
from datetime import datetime, timezone

from discord.ext import commands

from clowdbot.config import get_settings
from clowdbot.database import (
    get_event_by_id,
    get_event_stats,
    get_recent_events,
    log_command,
    log_event,
    search_events,
)
from clowdbot.monitoring.health import run_health_checks

__all__ = ["setup_commands"]

logger = logging.getLogger(__name__)

_start_time = time.time()


async def _log_cmd(ctx: commands.Context, cmd: str, args: str | None = None, response: str | None = None) -> None:  # type: ignore[type-arg]
    """Helper to log a command execution."""
    try:
        await log_command(
            user_id=str(ctx.author.id),
            username=str(ctx.author),
            command=cmd,
            args=args,
            channel=str(ctx.channel),
            response=response[:500] if response else None,
        )
    except Exception:
        logger.exception("Failed to log command")


def setup_commands(bot: commands.Bot) -> None:
    """Register all bot commands."""

    @bot.command(name="help")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def help_cmd(ctx: commands.Context) -> None:  # type: ignore[type-arg]
        """List all available commands."""
        help_text = (
            "**ClowdBot Commands** 🤖\n"
            "```\n"
            "!help              - Show this help message\n"
            "!status            - System status overview\n"
            "!events [n]        - Recent events (default 5, max 20)\n"
            "!event <id>        - Event detail by ID\n"
            "!deploy [env]      - Trigger deployment\n"
            "!incident <t>      - Create incident event\n"
            "!incidents [n]     - List recent incidents\n"
            "!resolve <id> <r>  - Resolve an incident\n"
            "!escalate <id>     - Escalate incident severity\n"
            "!health            - Run health checks\n"
            "!uptime            - Uptime statistics\n"
            "!version           - Version and environment\n"
            "!search <q>        - Search events\n"
            "```"
        )
        await ctx.send(help_text)
        await _log_cmd(ctx, "help", response=help_text)

    @bot.command(name="status")
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def status_cmd(ctx: commands.Context) -> None:  # type: ignore[type-arg]
        """Show system status overview."""
        settings = get_settings()
        stats = await get_event_stats()
        uptime_sec = round(time.time() - _start_time, 1)
        hours = int(uptime_sec // 3600)
        minutes = int((uptime_sec % 3600) // 60)

        msg = (
            "**📊 System Status**\n"
            f"• **Uptime:** {hours}h {minutes}m\n"
            f"• **Environment:** {settings.ENVIRONMENT}\n"
            f"• **Total Events:** {stats.get('total_events', 0)}\n"
            f"• **Last 24h:** {stats.get('last_24h', 0)}\n"
            f"• **Version:** {settings.APP_VERSION}\n"
        )
        await ctx.send(msg)
        await _log_cmd(ctx, "status", response=msg)

    @bot.command(name="events")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def events_cmd(ctx: commands.Context, count: int = 5) -> None:  # type: ignore[type-arg]
        """Show recent events."""
        count = min(max(count, 1), 20)
        events = await get_recent_events(limit=count)
        if not events:
            await ctx.send("📭 No events recorded yet.")
            await _log_cmd(ctx, "events", args=str(count), response="No events")
            return

        lines = [f"**📋 Last {len(events)} Events**"]
        for e in events:
            sev_emoji = {"info": "ℹ️", "warning": "⚠️", "error": "❌", "critical": "🔥"}.get(
                e.get("severity", "info"), "❔"
            )
            lines.append(f"{sev_emoji} `#{e['id']}` [{e.get('source', '?')}] {e.get('summary', '')[:80]}")

        msg = "\n".join(lines)
        await ctx.send(msg)
        await _log_cmd(ctx, "events", args=str(count), response=msg)

    @bot.command(name="event")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def event_cmd(ctx: commands.Context, event_id: int) -> None:  # type: ignore[type-arg]
        """Show event detail by ID."""
        event = await get_event_by_id(event_id)
        if not event:
            await ctx.send(f"❌ Event #{event_id} not found.")
            await _log_cmd(ctx, "event", args=str(event_id), response="Not found")
            return

        msg = (
            f"**Event #{event['id']}**\n"
            f"• **Source:** {event.get('source', '?')}\n"
            f"• **Type:** {event.get('event_type', '?')}\n"
            f"• **Severity:** {event.get('severity', '?')}\n"
            f"• **Summary:** {event.get('summary', '')}\n"
            f"• **Time:** {event.get('timestamp', '?')}\n"
        )
        if event.get("detail"):
            msg += f"• **Detail:** {event['detail'][:300]}\n"
        await ctx.send(msg)
        await _log_cmd(ctx, "event", args=str(event_id), response=msg)

    @bot.command(name="deploy")
    @commands.cooldown(1, 30, commands.BucketType.user)
    async def deploy_cmd(ctx: commands.Context, env: str = "staging") -> None:  # type: ignore[type-arg]
        """Trigger deployment (approval-gated placeholder)."""
        await log_event(
            source="discord",
            event_type="deploy_request",
            summary=f"Deployment to {env} requested by {ctx.author}",
            severity="warning",
            metadata={"environment": env, "user": str(ctx.author), "user_id": str(ctx.author.id)},
        )
        msg = (
            f"🚀 **Deployment Request**\n"
            f"• **Environment:** {env}\n"
            f"• **Requested by:** {ctx.author}\n"
            f"• **Status:** Logged (approval required)\n"
            f"_Note: Automated deployment not yet configured._"
        )
        await ctx.send(msg)
        await _log_cmd(ctx, "deploy", args=env, response=msg)

    @bot.command(name="incident")
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def incident_cmd(ctx: commands.Context, title: str, severity: str = "warning") -> None:  # type: ignore[type-arg]
        """Create an incident event."""
        valid_severities = ("info", "warning", "error", "critical")
        if severity not in valid_severities:
            await ctx.send(f"❌ Invalid severity. Use: {', '.join(valid_severities)}")
            return

        event_id = await log_event(
            source="discord",
            event_type="incident",
            summary=f"🚨 Incident: {title}",
            severity=severity,
            detail=f"Created by {ctx.author} in {ctx.channel}",
            metadata={"user": str(ctx.author), "user_id": str(ctx.author.id)},
        )
        msg = f"🚨 **Incident Created** (#{event_id})\n• **Title:** {title}\n• **Severity:** {severity}"
        await ctx.send(msg)
        await _log_cmd(ctx, "incident", args=f"{title} {severity}", response=msg)

    @bot.command(name="health")
    @commands.cooldown(1, 15, commands.BucketType.user)
    async def health_cmd(ctx: commands.Context) -> None:  # type: ignore[type-arg]
        """Run health checks."""
        results = await run_health_checks()
        overall = "✅ Healthy" if results.get("healthy", False) else "❌ Unhealthy"
        checks = results.get("checks", {})
        lines = [f"**🏥 Health Check:** {overall}"]
        for name, ok in checks.items():
            lines.append(f"  {'✅' if ok else '❌'} {name}")
        msg = "\n".join(lines)
        await ctx.send(msg)
        await _log_cmd(ctx, "health", response=msg)

    @bot.command(name="uptime")
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def uptime_cmd(ctx: commands.Context) -> None:  # type: ignore[type-arg]
        """Show uptime statistics."""
        uptime_sec = time.time() - _start_time
        days = int(uptime_sec // 86400)
        hours = int((uptime_sec % 86400) // 3600)
        minutes = int((uptime_sec % 3600) // 60)
        msg = (
            f"**⏱️ Uptime**\n"
            f"• **Running:** {days}d {hours}h {minutes}m\n"
            f"• **Since:** {datetime.fromtimestamp(_start_time, tz=timezone.utc).isoformat()}\n"
        )
        await ctx.send(msg)
        await _log_cmd(ctx, "uptime", response=msg)

    @bot.command(name="version")
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def version_cmd(ctx: commands.Context) -> None:  # type: ignore[type-arg]
        """Show version and environment info."""
        settings = get_settings()
        msg = (
            f"**🏷️ Version Info**\n"
            f"• **Version:** {settings.APP_VERSION}\n"
            f"• **Environment:** {settings.ENVIRONMENT}\n"
            f"• **Python:** {platform.python_version()}\n"
            f"• **Platform:** {platform.platform()}\n"
        )
        await ctx.send(msg)
        await _log_cmd(ctx, "version", response=msg)

    @bot.command(name="search")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def search_cmd(ctx: commands.Context, *, query: str) -> None:  # type: ignore[type-arg]
        """Search events by text."""
        results = await search_events(query, limit=10)
        if not results:
            await ctx.send(f"🔍 No events matching `{query}`.")
            await _log_cmd(ctx, "search", args=query, response="No results")
            return

        lines = [f"**🔍 Search Results for `{query}`** ({len(results)} found)"]
        for e in results:
            lines.append(f"• `#{e['id']}` [{e.get('severity', '?')}] {e.get('summary', '')[:80]}")
        msg = "\n".join(lines)
        await ctx.send(msg)
        await _log_cmd(ctx, "search", args=query, response=msg)

    @bot.command(name="incidents")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def incidents_cmd(ctx: commands.Context, count: int = 5) -> None:  # type: ignore[type-arg]
        """List recent incidents."""
        from clowdbot.incidents.service import IncidentService
        count = min(max(count, 1), 20)
        incidents = await IncidentService.list_all(limit=count)
        if not incidents:
            await ctx.send("📭 No incidents recorded.")
            await _log_cmd(ctx, "incidents", args=str(count))
            return
        sev_emoji = {"critical": "🔥", "high": "🔴", "medium": "🟡", "low": "🟢", "info": "ℹ️"}
        status_emoji = {"open": "🔓", "investigating": "🔍", "mitigating": "🔧", "resolved": "✅", "closed": "📁"}
        lines = [f"**🚨 Last {len(incidents)} Incidents**"]
        for inc in incidents:
            se = sev_emoji.get(inc.get("severity", ""), "❔")
            ste = status_emoji.get(inc.get("status", ""), "❔")
            lines.append(f"{se}{ste} `#{inc['id']}` [{inc.get('status','?')}] {inc.get('title','')[:60]}")
        msg = "\n".join(lines)
        await ctx.send(msg)
        await _log_cmd(ctx, "incidents", args=str(count), response=msg)

    @bot.command(name="resolve")
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def resolve_cmd(ctx: commands.Context, incident_id: int, *, resolution: str) -> None:  # type: ignore[type-arg]
        """Resolve an incident. Usage: !resolve <id> <resolution text>"""
        from clowdbot.incidents.service import IncidentService
        success = await IncidentService.resolve(incident_id, resolution, str(ctx.author))
        if success:
            msg = f"✅ Incident #{incident_id} resolved by {ctx.author}.\n**Resolution:** {resolution}"
        else:
            msg = f"❌ Could not resolve incident #{incident_id}. Not found or already resolved."
        await ctx.send(msg)
        await _log_cmd(ctx, "resolve", args=f"{incident_id} {resolution}", response=msg)

    @bot.command(name="escalate")
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def escalate_cmd(ctx: commands.Context, incident_id: int) -> None:  # type: ignore[type-arg]
        """Escalate an incident severity."""
        from clowdbot.incidents.service import IncidentService
        incident = await IncidentService.get(incident_id)
        if not incident:
            await ctx.send(f"❌ Incident #{incident_id} not found.")
            return
        sev_order = ["info", "low", "medium", "high", "critical"]
        current = incident.get("severity", "medium")
        idx = sev_order.index(current) if current in sev_order else 2
        if idx >= len(sev_order) - 1:
            await ctx.send(f"⚠️ Incident #{incident_id} is already at maximum severity (critical).")
            return
        new_sev = sev_order[idx + 1]
        await IncidentService.update(incident_id, severity=new_sev, status="investigating")
        msg = f"⬆️ Incident #{incident_id} escalated from **{current}** to **{new_sev}**"
        await ctx.send(msg)
        await _log_cmd(ctx, "escalate", args=str(incident_id), response=msg)

    logger.info("All bot commands registered")

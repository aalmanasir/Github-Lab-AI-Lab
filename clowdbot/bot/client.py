"""Discord bot client setup and lifecycle management."""

from __future__ import annotations

import logging

import discord
from discord.ext import commands

from clowdbot.config import get_settings

__all__ = ["create_bot", "bot_instance"]

logger = logging.getLogger(__name__)

bot_instance: commands.Bot | None = None
_bot_connected: bool = False


def is_bot_connected() -> bool:
    """Check if the Discord bot is connected."""
    return _bot_connected


def create_bot() -> commands.Bot:
    """Create and configure the Discord bot instance."""
    global bot_instance

    settings = get_settings()
    intents = discord.Intents.default()
    intents.message_content = True
    intents.guilds = True
    intents.members = False

    bot = commands.Bot(
        command_prefix=settings.DISCORD_COMMAND_PREFIX,
        intents=intents,
        help_command=None,  # We provide our own
        description="ClowdBot - Autonomous Operations Agent",
    )

    @bot.event
    async def on_ready() -> None:
        global _bot_connected
        _bot_connected = True
        logger.info("Discord bot connected as %s (ID: %s)", bot.user, bot.user.id if bot.user else "?")
        await bot.change_presence(
            activity=discord.Activity(type=discord.ActivityType.watching, name="systems 🟢")
        )

    @bot.event
    async def on_disconnect() -> None:
        global _bot_connected
        _bot_connected = False
        logger.warning("Discord bot disconnected")

    @bot.event
    async def on_command_error(ctx: commands.Context, error: commands.CommandError) -> None:  # type: ignore[type-arg]
        if isinstance(error, commands.CommandNotFound):
            return  # Ignore unknown commands
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"⏳ Command on cooldown. Try again in {error.retry_after:.1f}s")
            return
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"❌ Missing argument: `{error.param.name}`")
            return
        logger.exception("Command error in %s: %s", ctx.command, error)
        await ctx.send("❌ An error occurred processing that command.")

    bot_instance = bot
    return bot


async def start_bot(bot: commands.Bot) -> None:
    """Start the Discord bot (non-blocking for use with asyncio)."""
    settings = get_settings()
    if not settings.DISCORD_TOKEN:
        logger.warning("No DISCORD_TOKEN configured - bot will not start")
        return
    logger.info("Starting Discord bot...")
    try:
        await bot.start(settings.DISCORD_TOKEN)
    except discord.LoginFailure:
        logger.error("Invalid Discord token - bot cannot authenticate")
    except Exception:
        logger.exception("Discord bot failed to start")

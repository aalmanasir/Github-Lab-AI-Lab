"""Environment-based configuration using pydantic-settings."""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings

__all__ = ["Settings", "get_settings"]


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env file."""

    DISCORD_TOKEN: str = Field(default="", description="Discord bot token")
    DISCORD_COMMAND_PREFIX: str = Field(default="!", description="Bot command prefix")
    GITHUB_WEBHOOK_SECRET: str = Field(default="", description="GitHub webhook HMAC secret")
    GITHUB_TOKEN: str = Field(default="", description="GitHub API token")
    OPENAI_API_KEY: str = Field(default="", description="OpenAI API key")
    DATABASE_URL: str = Field(default="sqlite:///data/clowdbot.db", description="Database URL")
    API_HOST: str = Field(default="0.0.0.0", description="API server host")
    API_PORT: int = Field(default=8080, description="API server port")
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")
    ENVIRONMENT: str = Field(default="development", description="Runtime environment")
    ALLOWED_CHANNELS: list[str] = Field(default_factory=list, description="Allowed Discord channel IDs")
    ALERT_WEBHOOK_URL: str = Field(default="", description="Webhook URL for alerts (Discord/Slack)")
    APP_VERSION: str = Field(default="0.1.0", description="Application version")

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
    }

    @property
    def db_path(self) -> str:
        """Extract the file path from the SQLite URL."""
        return self.DATABASE_URL.replace("sqlite:///", "")


_settings: Settings | None = None


def get_settings() -> Settings:
    """Get cached settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings

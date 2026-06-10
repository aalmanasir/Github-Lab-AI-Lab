"""Tests for configuration loading."""

from __future__ import annotations

import os

import pytest

from clowdbot.config import Settings


def test_default_settings() -> None:
    """Test Settings loads with defaults."""
    s = Settings()
    assert s.API_PORT == 8080
    assert s.API_HOST == "0.0.0.0"
    assert s.DISCORD_COMMAND_PREFIX == "!"
    assert s.LOG_LEVEL == "INFO"
    assert s.APP_VERSION == "0.1.0"
    assert s.ALLOWED_CHANNELS == []


def test_settings_from_env() -> None:
    """Test Settings picks up environment variables."""
    os.environ["API_PORT"] = "9090"
    os.environ["ENVIRONMENT"] = "production"
    try:
        s = Settings()
        assert s.API_PORT == 9090
        assert s.ENVIRONMENT == "production"
    finally:
        os.environ.pop("API_PORT", None)
        os.environ.pop("ENVIRONMENT", None)


def test_db_path_property() -> None:
    """Test db_path extracts path from SQLite URL."""
    s = Settings(DATABASE_URL="sqlite:///data/test.db")
    assert s.db_path == "data/test.db"

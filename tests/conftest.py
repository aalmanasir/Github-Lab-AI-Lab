"""Shared test fixtures."""

from __future__ import annotations

import asyncio
import os
from typing import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

# Force test environment
os.environ["ENVIRONMENT"] = "test"
os.environ["DATABASE_URL"] = "sqlite:///test_data/test.db"
os.environ["DISCORD_TOKEN"] = ""
os.environ["GITHUB_WEBHOOK_SECRET"] = "test-secret-123"


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def db() -> AsyncGenerator[None, None]:
    """Initialize and tear down test database."""
    from clowdbot.database import close_db, init_db
    await init_db()
    yield
    await close_db()
    # Clean up test DB
    import shutil
    shutil.rmtree("test_data", ignore_errors=True)


@pytest_asyncio.fixture
async def client(db: None) -> AsyncGenerator[AsyncClient, None]:
    """Create test HTTP client with app."""
    # Re-import to get fresh app with test config
    from main import create_app
    app = create_app()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

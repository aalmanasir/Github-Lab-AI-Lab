# Architecture

## Overview

ClowdBot is an autonomous operations agent built with Python, combining a FastAPI REST API with a Discord bot in a single process. It receives events from GitHub webhooks, provides a command interface via Discord, and exposes a REST API for status, events, and manual triggers.

## Components

### FastAPI API Server
- **Health endpoints** (`/health`, `/ready`) — liveness and readiness probes
- **Status dashboard** (`/api/status`) — system overview with uptime, event stats, bot status
- **Events API** (`/api/events`) — paginated, filterable event history
- **Triggers** (`/api/trigger/*`) — manual health checks, alert tests, event injection
- **GitHub webhooks** (`/webhooks/github`) — receives and processes GitHub events

### Discord Bot
- Built with discord.py, runs concurrently with FastAPI via asyncio
- Commands for status, events, deployments, incidents, health checks
- Posts notifications for important GitHub events to configured channels

### Database (SQLite)
- Async access via aiosqlite
- Tables: `event_log`, `command_log`, `webhook_log`, `uptime_log`
- All operations are non-blocking

### Monitoring
- **Health checks** — composite DB + bot + API health
- **Alerts** — webhook-based (Discord/Slack embed format)
- **Uptime tracking** — periodic self-checks logged to `uptime_log`

## Data Flow

```
GitHub → Webhook POST → Verify HMAC → Log → Event Log → Discord Notification
                                                       → API Query
Discord User → Bot Command → Process → DB Query → Response
                                     → Log Command
External → REST API → Query/Trigger → DB → JSON Response
```

## Technology Stack

| Component | Technology |
|-----------|-----------|
| API Framework | FastAPI + Uvicorn |
| Bot | discord.py |
| Database | SQLite (aiosqlite) |
| Config | pydantic-settings |
| HTTP Client | aiohttp |
| Containerization | Docker |
| CI/CD | GitHub Actions |

## Deployment

Single Docker container running both API server and Discord bot. Data persisted via Docker volume at `/app/data`. Configuration via environment variables (`.env` file).

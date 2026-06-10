# ClowdBot Agent

![CI](https://github.com/clowdops/clowdbot-agent/actions/workflows/ci.yml/badge.svg)
![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)
![License: MIT](https://img.shields.io/badge/license-MIT-green)

Autonomous operations agent that combines a Discord bot, REST API, and webhook handler for infrastructure monitoring, event logging, and operational command-and-control. Events are persisted to SQLite, alerts are routed through configurable webhooks, and the whole thing runs in a single Docker container.

## Architecture

```
┌─────────────────────────────────────────────┐
│                  ClowdBot                    │
│                                              │
│  ┌──────────┐  ┌──────────┐  ┌───────────┐  │
│  │ Discord  │  │ FastAPI  │  │  Webhook   │  │
│  │   Bot    │  │   API    │  │  Handlers  │  │
│  └────┬─────┘  └────┬─────┘  └─────┬─────┘  │
│       │              │              │         │
│       └──────────┬───┘──────────────┘         │
│                  │                             │
│          ┌───────▼────────┐                   │
│          │   SQLite DB    │                   │
│          │  (event log)   │                   │
│          └────────────────┘                   │
│                                              │
│  ┌──────────┐  ┌──────────┐                  │
│  │ Uptime   │  │  Alert   │                  │
│  │ Monitor  │  │ Pipeline │                  │
│  └──────────┘  └──────────┘                  │
└─────────────────────────────────────────────┘
```

## Quick Start

```bash
cp .env.example .env        # Configure credentials
make install                # Install dependencies
make run                    # Start the agent
```

## Setup

### Prerequisites

- Python 3.11+
- Discord bot token ([create one](https://discord.com/developers/applications))
- (Optional) GitHub webhook secret, OpenAI API key

### Installation

```bash
# Clone the repo
git clone https://github.com/clowdops/clowdbot-agent.git
cd clowdbot-agent

# Create virtual environment
python -m venv .venv && source .venv/bin/activate

# Install dependencies
make install          # production
make dev              # development (includes test/lint tools)

# Configure environment
cp .env.example .env
# Edit .env with your tokens
```

### Run

```bash
# Direct
make run

# Docker
make docker-build
make docker-run
```

## Configuration

| Variable | Default | Description |
|---|---|---|
| `DISCORD_TOKEN` | _(required)_ | Discord bot token |
| `DISCORD_COMMAND_PREFIX` | `!` | Bot command prefix |
| `GITHUB_WEBHOOK_SECRET` | _(empty)_ | GitHub webhook HMAC secret |
| `GITHUB_TOKEN` | _(empty)_ | GitHub API token |
| `OPENAI_API_KEY` | _(empty)_ | OpenAI API key |
| `DATABASE_URL` | `sqlite:///data/clowdbot.db` | Database URL |
| `API_HOST` | `0.0.0.0` | API listen host |
| `API_PORT` | `8080` | API listen port |
| `LOG_LEVEL` | `INFO` | Logging level |
| `ENVIRONMENT` | `development` | Runtime environment |
| `ALLOWED_CHANNELS` | _(empty)_ | Allowed Discord channel IDs (JSON list) |
| `ALERT_WEBHOOK_URL` | _(empty)_ | Webhook URL for alerts (Discord/Slack) |

## API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Liveness probe |
| `GET` | `/ready` | Readiness probe (checks DB) |
| `GET` | `/api/status` | System dashboard |
| `GET` | `/api/events` | List events (filterable) |
| `GET` | `/api/events/{id}` | Get event by ID |
| `GET` | `/api/events/stats` | Event statistics |
| `GET` | `/api/events/search?q=...` | Search events |
| `POST` | `/api/trigger/health-check` | Manual health check |
| `POST` | `/api/trigger/event` | Inject manual event |
| `POST` | `/api/trigger/alert-test` | Test alert pipeline |
| `POST` | `/webhooks/github` | GitHub webhook receiver |

## Discord Commands

| Command | Description |
|---|---|
| `!ping` | Bot latency check |
| `!status` | System status summary |
| `!events [n]` | Recent events |
| `!deploy` | Deployment status |
| `!incident <msg>` | Create incident event |

## Docker

```bash
# Build
docker build -t clowdbot-agent .

# Run with docker-compose
docker-compose up -d

# Check health
curl http://localhost:8080/health
```

The container runs as a non-root user, includes a health check, and persists data via a volume mount at `/app/data`.

## Development

```bash
# Install dev dependencies
make dev

# Run linter
make lint

# Auto-format
make format

# Type check
make typecheck

# Run tests
make test

# Run all checks
make all
```

## Project Structure

```
clowdbot-agent/
├── main.py                     # Entrypoint - FastAPI + Discord bot
├── clowdbot/
│   ├── __init__.py
│   ├── config.py               # Pydantic settings
│   ├── database.py             # SQLite async operations
│   ├── database_migrations.py  # Schema versioning
│   ├── logging_config.py       # Structured logging setup
│   ├── models.py               # Pydantic models
│   ├── api/
│   │   ├── events.py           # Event CRUD endpoints
│   │   ├── health.py           # Health/readiness probes
│   │   ├── middleware.py        # Rate limiting, logging, CORS
│   │   ├── router.py           # API router aggregation
│   │   ├── status.py           # Status dashboard
│   │   └── triggers.py         # Manual trigger endpoints
│   ├── bot/
│   │   ├── client.py           # Discord bot client
│   │   └── commands.py         # Bot command handlers
│   ├── monitoring/
│   │   ├── alerts.py           # Alert pipeline
│   │   ├── health.py           # Health check logic
│   │   └── uptime.py           # Uptime monitor
│   └── webhooks/
│       ├── github.py           # GitHub webhook handler
│       └── verify.py           # Webhook signature verification
├── tests/
│   ├── conftest.py             # Shared fixtures
│   ├── test_config.py
│   ├── test_events.py
│   ├── test_health.py
│   ├── test_status.py
│   ├── test_triggers.py
│   └── test_webhooks.py
├── docs/
│   ├── API.md
│   ├── ARCHITECTURE.md
│   └── RUNBOOK.md
├── Dockerfile
├── docker-compose.yml
├── Makefile
├── pyproject.toml
├── ruff.toml
├── requirements.txt
└── requirements-dev.txt
```

## License

MIT

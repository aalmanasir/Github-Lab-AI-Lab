# Runbook

## Setup

### Prerequisites
- Python 3.11+
- Docker (optional, for containerized deployment)
- Discord bot token (from Discord Developer Portal)
- GitHub webhook secret (for webhook integration)

### Local Development

```bash
# Clone and install
pip install -r requirements.txt

# Configure
cp .env.example .env
# Edit .env with your values

# Run
python main.py
```

### Docker Deployment

```bash
# Build and run
cp .env.example .env
# Edit .env
docker-compose up -d

# View logs
docker-compose logs -f clowdbot

# Stop
docker-compose down
```

## Configuration

All configuration is via environment variables. See `.env.example` for all options.

Key variables:
- `DISCORD_TOKEN` — Required for Discord bot functionality
- `GITHUB_WEBHOOK_SECRET` — Required for webhook signature verification
- `DATABASE_URL` — SQLite path (default: `sqlite:///data/clowdbot.db`)
- `API_PORT` — API server port (default: 8080)

## GitHub Webhook Setup

1. Go to your repo → Settings → Webhooks → Add webhook
2. Payload URL: `https://your-domain:8080/webhooks/github`
3. Content type: `application/json`
4. Secret: Same as `GITHUB_WEBHOOK_SECRET` in your `.env`
5. Events: Select individual events or "Send me everything"

## Troubleshooting

### Bot won't connect
- Verify `DISCORD_TOKEN` is correct
- Check bot has proper intents enabled in Discord Developer Portal
- Ensure message content intent is enabled

### Webhooks failing
- Check `GITHUB_WEBHOOK_SECRET` matches GitHub config
- Verify the endpoint is publicly accessible
- Check logs for signature verification errors

### Database errors
- Ensure `data/` directory exists and is writable
- Check file permissions (especially in Docker)

### Health check failing
- `GET /health` — basic liveness
- `GET /ready` — DB connectivity check
- Check logs for specific error messages

## Common Operations

### View recent events
```bash
curl http://localhost:8080/api/events?limit=10
```

### Trigger health check
```bash
curl -X POST http://localhost:8080/api/trigger/health-check
```

### Inject manual event
```bash
curl -X POST http://localhost:8080/api/trigger/event \
  -H "Content-Type: application/json" \
  -d '{"source": "manual", "summary": "Test event", "severity": "info"}'
```

### Check status
```bash
curl http://localhost:8080/api/status
```

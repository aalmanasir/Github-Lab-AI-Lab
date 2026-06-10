# API Reference

Base URL: `http://localhost:8080`

All responses use a standard envelope:
```json
{
  "status": "ok|error",
  "data": { ... },
  "error": "message (if status=error)",
  "timestamp": "ISO 8601"
}
```

## Health

### GET /health
Basic health check.

**Response:**
```json
{
  "status": "ok",
  "data": {
    "status": "healthy",
    "timestamp": "2024-01-01T00:00:00Z",
    "version": "0.1.0"
  }
}
```

### GET /ready
Readiness probe (checks DB connectivity).

**Response:**
```json
{
  "status": "ok",
  "data": { "ready": true, "database": "connected" }
}
```

## Status

### GET /api/status
System dashboard with uptime, events, and system info.

**Response:**
```json
{
  "status": "ok",
  "data": {
    "uptime_seconds": 3600.5,
    "environment": "development",
    "version": "0.1.0",
    "event_stats": { "total_events": 42, "last_24h": 10, ... },
    "recent_events": [ ... ],
    "bot_connected": true,
    "system_info": { "python": "3.11.7", "platform": "...", "hostname": "..." }
  }
}
```

## Events

### GET /api/events
Paginated event history.

**Query Parameters:**
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| source | string | — | Filter by source |
| type | string | — | Filter by event type |
| severity | string | — | Filter by severity (info/warning/error/critical) |
| since | string | — | ISO timestamp lower bound |
| until | string | — | ISO timestamp upper bound |
| limit | int | 50 | Results per page (1-200) |
| offset | int | 0 | Pagination offset |

### GET /api/events/{id}
Get a single event by ID.

### GET /api/events/stats
Aggregate event statistics.

**Response:**
```json
{
  "status": "ok",
  "data": {
    "total_events": 100,
    "last_24h": 15,
    "by_severity": { "info": 80, "warning": 15, "error": 5 },
    "by_source": { "github": 60, "discord": 30, "api": 10 }
  }
}
```

### GET /api/events/search?q=query
Search events by summary or detail text.

## Triggers

### POST /api/trigger/health-check
Run health checks manually.

### POST /api/trigger/alert-test
Test the alert delivery pipeline.

### POST /api/trigger/event
Inject a manual event.

**Request Body:**
```json
{
  "source": "manual",
  "event_type": "manual",
  "severity": "info",
  "summary": "Test event",
  "detail": "Optional detail text",
  "metadata": { "key": "value" }
}
```

## Incidents

### POST /api/incidents
Create a new incident with automatic classification and recommendations.

**Request Body:**
```json
{
  "title": "Production API returning 503",
  "description": "All endpoints returning 503 since 14:00 UTC",
  "source": "monitoring",
  "severity": "critical",
  "incident_type": "outage",
  "metadata": { "region": "us-east-1" },
  "use_ai": false
}
```
Only `title` is required. If `severity` and `incident_type` are omitted, the system auto-classifies based on title/description text.

**Response:**
```json
{
  "status": "ok",
  "data": {
    "incident": { "id": 1, "title": "...", "status": "open", ... },
    "classification": { "incident_type": "outage", "severity": "critical", "confidence": 0.95, ... },
    "recommendations": { "playbook": { ... }, "recommendation_text": "...", ... }
  }
}
```

### GET /api/incidents
List incidents with optional filters.

**Query Parameters:**
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| status | string | — | Filter by status (open/investigating/mitigating/resolved/closed) |
| severity | string | — | Filter by severity (critical/high/medium/low/info) |
| limit | int | 50 | Results per page (1-200) |
| offset | int | 0 | Pagination offset |

**Response:**
```json
{
  "status": "ok",
  "data": { "incidents": [ ... ], "count": 5 }
}
```

### GET /api/incidents/stats
Aggregate incident statistics.

**Response:**
```json
{
  "status": "ok",
  "data": {
    "total_incidents": 42,
    "by_status": { "open": 5, "resolved": 30, "closed": 7 },
    "by_severity": { "critical": 3, "high": 10, "medium": 20, "low": 9 },
    "avg_resolution_seconds": 3600.5
  }
}
```

### GET /api/incidents/{id}
Get a single incident by ID.

### PATCH /api/incidents/{id}
Update incident fields.

**Request Body:**
```json
{
  "severity": "critical",
  "status": "investigating",
  "assigned_to": "oncall-team"
}
```

### POST /api/incidents/{id}/resolve
Resolve an incident.

**Request Body:**
```json
{
  "resolution": "Rolled back deploy v2.3.1, service restored",
  "resolved_by": "jane@example.com"
}
```

## Webhooks

### POST /webhooks/github
GitHub webhook receiver.

**Headers:**
- `X-Hub-Signature-256` — HMAC signature
- `X-GitHub-Event` — Event type
- `X-GitHub-Delivery` — Delivery ID

**Supported Events:** push, pull_request, issues, release, check_suite, check_run, create, delete, star, fork

"""GitHub webhook handler - processes push, PR, issue, release, CI events."""

from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Request

from clowdbot.config import get_settings
from clowdbot.database import log_event, log_webhook
from clowdbot.models import APIResponse
from clowdbot.webhooks.verify import verify_github_signature

__all__ = ["router", "format_github_event"]

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/webhooks", tags=["webhooks"])


def _summarize_push(payload: dict[str, Any]) -> tuple[str, str]:
    """Summarize a push event."""
    ref = payload.get("ref", "unknown")
    commits = payload.get("commits", [])
    pusher = payload.get("pusher", {}).get("name", "unknown")
    repo = payload.get("repository", {}).get("full_name", "unknown")
    branch = ref.replace("refs/heads/", "")
    summary = f"📦 {pusher} pushed {len(commits)} commit(s) to {repo}/{branch}"
    details = "\n".join(f"• {c.get('message', '').split(chr(10))[0]}" for c in commits[:5])
    return summary, details


def _summarize_pull_request(payload: dict[str, Any]) -> tuple[str, str]:
    """Summarize a pull_request event."""
    action = payload.get("action", "unknown")
    pr = payload.get("pull_request", {})
    title = pr.get("title", "untitled")
    number = pr.get("number", "?")
    user = pr.get("user", {}).get("login", "unknown")
    merged = pr.get("merged", False)
    repo = payload.get("repository", {}).get("full_name", "unknown")

    if action == "closed" and merged:
        emoji = "🟣"
        action = "merged"
    elif action == "opened":
        emoji = "🟢"
    elif action == "closed":
        emoji = "🔴"
    else:
        emoji = "🔵"

    summary = f"{emoji} PR #{number} {action} by {user}: {title} ({repo})"
    detail = pr.get("body", "") or ""
    return summary, detail[:500]


def _summarize_issues(payload: dict[str, Any]) -> tuple[str, str]:
    """Summarize an issues event."""
    action = payload.get("action", "unknown")
    issue = payload.get("issue", {})
    title = issue.get("title", "untitled")
    number = issue.get("number", "?")
    user = issue.get("user", {}).get("login", "unknown")
    repo = payload.get("repository", {}).get("full_name", "unknown")
    emoji = "🟢" if action == "opened" else "🔴" if action == "closed" else "🏷️"
    summary = f"{emoji} Issue #{number} {action} by {user}: {title} ({repo})"
    detail = issue.get("body", "") or ""
    return summary, detail[:500]


def _summarize_release(payload: dict[str, Any]) -> tuple[str, str]:
    """Summarize a release event."""
    release = payload.get("release", {})
    tag = release.get("tag_name", "unknown")
    name = release.get("name", tag)
    author = release.get("author", {}).get("login", "unknown")
    repo = payload.get("repository", {}).get("full_name", "unknown")
    summary = f"🚀 Release {tag} published by {author}: {name} ({repo})"
    detail = release.get("body", "") or ""
    return summary, detail[:500]


def _summarize_check(payload: dict[str, Any], event_type: str) -> tuple[str, str]:
    """Summarize check_suite or check_run events."""
    if event_type == "check_suite":
        suite = payload.get("check_suite", {})
        status = suite.get("conclusion", suite.get("status", "unknown"))
        branch = suite.get("head_branch", "unknown")
    else:
        run = payload.get("check_run", {})
        status = run.get("conclusion", run.get("status", "unknown"))
        branch = run.get("check_suite", {}).get("head_branch", "unknown")

    repo = payload.get("repository", {}).get("full_name", "unknown")
    emoji = "✅" if status == "success" else "❌" if status == "failure" else "⏳"
    summary = f"{emoji} CI {event_type} {status} on {repo}/{branch}"
    return summary, ""


def _summarize_generic(payload: dict[str, Any], event_type: str) -> tuple[str, str]:
    """Summarize generic events (star, fork, create, delete)."""
    repo = payload.get("repository", {}).get("full_name", "unknown")
    sender = payload.get("sender", {}).get("login", "unknown")
    summary = f"📌 {event_type} event on {repo} by {sender}"
    return summary, ""


def format_github_event(event_type: str, payload: dict[str, Any]) -> tuple[str, str, str]:
    """Format a GitHub event into summary, detail, and severity.

    Returns:
        Tuple of (summary, detail, severity).
    """
    handlers = {
        "push": _summarize_push,
        "pull_request": _summarize_pull_request,
        "issues": _summarize_issues,
        "release": _summarize_release,
    }

    if event_type in handlers:
        summary, detail = handlers[event_type](payload)
    elif event_type in ("check_suite", "check_run"):
        summary, detail = _summarize_check(payload, event_type)
    else:
        summary, detail = _summarize_generic(payload, event_type)

    # Determine severity
    severity = "info"
    if event_type in ("check_suite", "check_run"):
        conclusion = payload.get(event_type.replace("_", "_"), {}).get("conclusion", "")
        if conclusion == "failure":
            severity = "error"
    elif event_type == "release":
        severity = "info"

    return summary, detail, severity


@router.post("/github")
async def github_webhook(
    request: Request,
    x_hub_signature_256: str | None = Header(None),
    x_github_event: str | None = Header(None),
    x_github_delivery: str | None = Header(None),
) -> APIResponse:
    """Handle incoming GitHub webhook events."""
    settings = get_settings()
    body = await request.body()

    # Verify signature if secret is configured
    if settings.GITHUB_WEBHOOK_SECRET:
        if not x_hub_signature_256:
            raise HTTPException(status_code=401, detail="Missing signature header")
        if not verify_github_signature(body, x_hub_signature_256, settings.GITHUB_WEBHOOK_SECRET):
            raise HTTPException(status_code=401, detail="Invalid signature")

    event_type = x_github_event or "unknown"
    delivery_id = x_github_delivery or ""

    try:
        payload = json.loads(body)
    except json.JSONDecodeError as e:
        logger.error("Failed to parse webhook payload: %s", e)
        raise HTTPException(status_code=400, detail="Invalid JSON payload") from e

    logger.info("Received GitHub webhook: %s (delivery: %s)", event_type, delivery_id)

    # Log to webhook_log
    await log_webhook(
        provider="github",
        event_type=event_type,
        delivery_id=delivery_id,
        payload=json.dumps(payload)[:10000],  # Truncate large payloads
        processed=True,
    )

    # Format and log to event_log
    summary, detail, severity = format_github_event(event_type, payload)
    event_id = await log_event(
        source="github",
        event_type=event_type,
        summary=summary,
        severity=severity,
        detail=detail,
        metadata={
            "delivery_id": delivery_id,
            "repo": payload.get("repository", {}).get("full_name", ""),
            "sender": payload.get("sender", {}).get("login", ""),
        },
    )

    return APIResponse(
        status="ok",
        data={"event_type": event_type, "event_id": event_id, "delivery_id": delivery_id},
    )

"""Tests for GitHub webhook handling."""

from __future__ import annotations

import hashlib
import hmac
import json

import pytest
from httpx import AsyncClient

from clowdbot.webhooks.verify import verify_github_signature


def test_verify_valid_signature() -> None:
    """Test HMAC verification with correct signature."""
    secret = "test-secret-123"
    payload = b'{"action": "opened"}'
    sig = "sha256=" + hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    assert verify_github_signature(payload, sig, secret) is True


def test_verify_invalid_signature() -> None:
    """Test HMAC verification with incorrect signature."""
    assert verify_github_signature(b"payload", "sha256=invalid", "secret") is False


def test_verify_missing_signature() -> None:
    """Test HMAC verification with empty signature."""
    assert verify_github_signature(b"payload", "", "secret") is False


def test_verify_bad_format() -> None:
    """Test HMAC verification with wrong prefix."""
    assert verify_github_signature(b"payload", "md5=abc", "secret") is False


@pytest.mark.asyncio
async def test_github_webhook_push(client: AsyncClient) -> None:
    """Test processing a GitHub push webhook."""
    payload = {
        "ref": "refs/heads/main",
        "commits": [{"message": "fix: update readme"}],
        "pusher": {"name": "testuser"},
        "repository": {"full_name": "org/repo"},
        "sender": {"login": "testuser"},
    }
    body = json.dumps(payload).encode()
    secret = "test-secret-123"
    sig = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()

    resp = await client.post(
        "/webhooks/github",
        content=body,
        headers={
            "X-Hub-Signature-256": sig,
            "X-GitHub-Event": "push",
            "X-GitHub-Delivery": "test-delivery-1",
            "Content-Type": "application/json",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["data"]["event_type"] == "push"


@pytest.mark.asyncio
async def test_github_webhook_invalid_signature(client: AsyncClient) -> None:
    """Test webhook rejection with invalid signature."""
    resp = await client.post(
        "/webhooks/github",
        content=b'{"test": true}',
        headers={
            "X-Hub-Signature-256": "sha256=invalidsignature",
            "X-GitHub-Event": "push",
            "Content-Type": "application/json",
        },
    )
    assert resp.status_code == 401

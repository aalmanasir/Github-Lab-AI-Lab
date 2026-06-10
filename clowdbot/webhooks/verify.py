"""HMAC signature verification for webhooks."""

from __future__ import annotations

import hashlib
import hmac
import logging

__all__ = ["verify_github_signature"]

logger = logging.getLogger(__name__)


def verify_github_signature(payload: bytes, signature: str, secret: str) -> bool:
    """Verify GitHub webhook HMAC-SHA256 signature (timing-safe).

    Args:
        payload: Raw request body bytes.
        signature: Value of X-Hub-Signature-256 header.
        secret: The configured webhook secret.

    Returns:
        True if signature is valid, False otherwise.
    """
    if not signature or not secret:
        logger.warning("Missing signature or secret for webhook verification")
        return False

    if not signature.startswith("sha256="):
        logger.warning("Invalid signature format: %s", signature[:20])
        return False

    expected = "sha256=" + hmac.new(
        secret.encode("utf-8"),
        payload,
        hashlib.sha256,
    ).hexdigest()

    is_valid = hmac.compare_digest(expected, signature)
    if not is_valid:
        logger.warning("Webhook signature mismatch")
    return is_valid

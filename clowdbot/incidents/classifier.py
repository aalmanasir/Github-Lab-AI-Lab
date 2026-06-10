"""Incident classification engine - rule-based with optional AI."""

from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

# Classification rules: patterns -> (incident_type, severity_adjustment)
CLASSIFICATION_RULES: list[dict[str, Any]] = [
    {
        "patterns": [r"(?i)outage", r"(?i)down", r"(?i)unreachable", r"(?i)502", r"(?i)503"],
        "type": "outage",
        "severity": "critical",
        "confidence": 0.9,
    },
    {
        "patterns": [r"(?i)security", r"(?i)breach", r"(?i)unauthorized", r"(?i)vulnerability", r"(?i)CVE-"],
        "type": "security",
        "severity": "critical",
        "confidence": 0.85,
    },
    {
        "patterns": [r"(?i)slow", r"(?i)latency", r"(?i)timeout", r"(?i)performance", r"(?i)degraded"],
        "type": "performance",
        "severity": "high",
        "confidence": 0.8,
    },
    {
        "patterns": [r"(?i)deploy", r"(?i)rollback", r"(?i)release", r"(?i)build.+fail"],
        "type": "deployment",
        "severity": "high",
        "confidence": 0.8,
    },
    {
        "patterns": [r"(?i)disk", r"(?i)memory", r"(?i)cpu", r"(?i)capacity", r"(?i)storage"],
        "type": "infrastructure",
        "severity": "medium",
        "confidence": 0.75,
    },
    {
        "patterns": [r"(?i)error", r"(?i)exception", r"(?i)crash", r"(?i)fail"],
        "type": "application_error",
        "severity": "medium",
        "confidence": 0.7,
    },
    {
        "patterns": [r"(?i)config", r"(?i)misconfigur", r"(?i)setting"],
        "type": "configuration",
        "severity": "low",
        "confidence": 0.7,
    },
    {
        "patterns": [r"(?i)alert", r"(?i)warning", r"(?i)notice"],
        "type": "alert",
        "severity": "low",
        "confidence": 0.6,
    },
]

# Pre-compile all regex patterns once at module load to avoid repeated compilation.
_COMPILED_RULES: list[tuple[dict[str, Any], list[re.Pattern[str]]]] = [
    (rule, [re.compile(p) for p in rule["patterns"]])
    for rule in CLASSIFICATION_RULES
]

SEVERITY_ORDER = {"critical": 4, "high": 3, "medium": 2, "low": 1, "info": 0}


def classify_incident(
    title: str,
    description: str | None = None,
    source: str = "manual",
) -> dict[str, Any]:
    """Classify an incident based on title and description.

    Returns dict with: incident_type, severity, confidence, matched_rules, reasoning
    """
    text = f"{title} {description or ''}".strip()
    matched: list[dict[str, Any]] = []

    for rule, compiled_patterns in _COMPILED_RULES:
        for pattern in compiled_patterns:
            if pattern.search(text):
                matched.append(rule)
                break

    if not matched:
        return {
            "incident_type": "unknown",
            "severity": "medium",
            "confidence": 0.3,
            "matched_rules": 0,
            "reasoning": "No classification rules matched. Defaulting to unknown/medium.",
        }

    # Pick highest severity match
    best = max(matched, key=lambda r: SEVERITY_ORDER.get(r["severity"], 0))

    # Boost confidence if multiple rules match
    confidence = min(best["confidence"] + (len(matched) - 1) * 0.05, 0.99)

    # Source-based adjustments
    if source in ("monitoring", "alertmanager", "datadog", "pagerduty"):
        confidence = min(confidence + 0.05, 0.99)

    reasoning_parts = [f"Matched {len(matched)} rule(s)."]
    reasoning_parts.append(f"Primary classification: {best['type']} ({best['severity']}).")
    if len(matched) > 1:
        # dict.fromkeys preserves insertion order while deduplicating
        types = list(dict.fromkeys(r["type"] for r in matched))
        reasoning_parts.append(f"Also matched: {', '.join(types)}.")

    return {
        "incident_type": best["type"],
        "severity": best["severity"],
        "confidence": round(confidence, 2),
        "matched_rules": len(matched),
        "reasoning": " ".join(reasoning_parts),
    }


async def classify_with_ai(
    title: str,
    description: str | None = None,
) -> dict[str, Any] | None:
    """Optional AI-powered classification using OpenAI.

    Returns classification dict or None if unavailable.
    """
    try:
        from clowdbot.config import get_settings
        settings = get_settings()
        if not settings.OPENAI_API_KEY:
            return None

        import openai
        client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an incident classification engine. Given an incident title and description, "
                        "classify it into exactly one type and severity. "
                        "Types: outage, security, performance, deployment, infrastructure, application_error, configuration, alert, unknown. "
                        "Severities: critical, high, medium, low, info. "
                        "Respond in JSON: {\"incident_type\": \"...\", \"severity\": \"...\", \"confidence\": 0.0-1.0, \"reasoning\": \"...\"}"
                    ),
                },
                {
                    "role": "user",
                    "content": f"Title: {title}\nDescription: {description or 'N/A'}",
                },
            ],
            temperature=0.1,
            max_tokens=200,
        )

        import json
        content = response.choices[0].message.content or "{}"
        # Strip markdown code fences if present
        content = content.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[1].rsplit("```", 1)[0]

        result = json.loads(content)
        result["source"] = "ai"
        return result

    except ImportError:
        logger.debug("openai package not installed - AI classification unavailable")
        return None
    except Exception:
        logger.exception("AI classification failed")
        return None

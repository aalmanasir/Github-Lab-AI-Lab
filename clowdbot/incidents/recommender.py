"""Incident response recommendation engine."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# Response playbooks by incident type
PLAYBOOKS: dict[str, dict[str, Any]] = {
    "outage": {
        "immediate_actions": [
            "Check service health dashboards",
            "Verify infrastructure status (load balancers, DNS, compute)",
            "Check for recent deployments that may have caused the outage",
            "Initiate status page update",
            "Notify on-call team",
        ],
        "investigation_steps": [
            "Review application logs for errors",
            "Check database connectivity and performance",
            "Verify external dependency availability",
            "Review resource utilization (CPU, memory, disk)",
            "Check network connectivity between services",
        ],
        "escalation_threshold_minutes": 15,
        "communication_template": "Service {title} is currently experiencing an outage. Team is investigating. ETA for update: {eta}.",
    },
    "security": {
        "immediate_actions": [
            "Assess scope of potential breach",
            "Isolate affected systems if necessary",
            "Preserve logs and evidence",
            "Notify security team lead",
            "Check for active exploitation",
        ],
        "investigation_steps": [
            "Review access logs for suspicious activity",
            "Scan for indicators of compromise",
            "Check for unauthorized configuration changes",
            "Review network traffic patterns",
            "Verify credential integrity",
        ],
        "escalation_threshold_minutes": 5,
        "communication_template": "Security incident detected: {title}. Security team engaged. Do not discuss details outside secure channels.",
    },
    "performance": {
        "immediate_actions": [
            "Check current resource utilization",
            "Review recent traffic patterns for anomalies",
            "Check for slow database queries",
            "Verify CDN and cache health",
            "Consider scaling resources if threshold exceeded",
        ],
        "investigation_steps": [
            "Profile application performance",
            "Review APM traces for bottlenecks",
            "Check database query execution plans",
            "Review recent code changes",
            "Analyze traffic patterns for abuse",
        ],
        "escalation_threshold_minutes": 30,
        "communication_template": "Performance degradation detected in {title}. Team is optimizing. Users may experience slower response times.",
    },
    "deployment": {
        "immediate_actions": [
            "Verify deployment status and health checks",
            "Check rollback readiness",
            "Review deployment logs for errors",
            "Monitor error rates post-deployment",
            "Notify release manager",
        ],
        "investigation_steps": [
            "Compare pre/post deployment metrics",
            "Review changed files and configurations",
            "Check for database migration issues",
            "Verify environment variable changes",
            "Run smoke tests against deployment",
        ],
        "escalation_threshold_minutes": 20,
        "communication_template": "Deployment issue detected: {title}. Evaluating rollback. Monitoring in progress.",
    },
    "infrastructure": {
        "immediate_actions": [
            "Check resource utilization trends",
            "Verify autoscaling policies",
            "Review capacity forecasts",
            "Check for hardware failures or alerts",
            "Assess impact on services",
        ],
        "investigation_steps": [
            "Review resource consumption history",
            "Check for resource leaks",
            "Verify infrastructure provisioning",
            "Review scheduled maintenance windows",
            "Assess capacity planning needs",
        ],
        "escalation_threshold_minutes": 30,
        "communication_template": "Infrastructure issue: {title}. Operations team investigating. Service impact being assessed.",
    },
}

DEFAULT_PLAYBOOK: dict[str, Any] = {
    "immediate_actions": [
        "Acknowledge the incident",
        "Assess severity and impact",
        "Identify affected systems and users",
        "Begin investigation",
        "Notify relevant team members",
    ],
    "investigation_steps": [
        "Review related logs and metrics",
        "Check for recent changes",
        "Identify root cause",
        "Document findings",
        "Determine resolution path",
    ],
    "escalation_threshold_minutes": 30,
    "communication_template": "Incident reported: {title}. Team is investigating.",
}

SEVERITY_RESPONSE = {
    "critical": {
        "response_time_target": "5 minutes",
        "update_frequency": "Every 15 minutes",
        "requires_war_room": True,
        "auto_escalate": True,
        "notification_channels": ["pagerduty", "slack", "email"],
    },
    "high": {
        "response_time_target": "15 minutes",
        "update_frequency": "Every 30 minutes",
        "requires_war_room": False,
        "auto_escalate": True,
        "notification_channels": ["slack", "email"],
    },
    "medium": {
        "response_time_target": "1 hour",
        "update_frequency": "Every 2 hours",
        "requires_war_room": False,
        "auto_escalate": False,
        "notification_channels": ["slack"],
    },
    "low": {
        "response_time_target": "4 hours",
        "update_frequency": "Daily",
        "requires_war_room": False,
        "auto_escalate": False,
        "notification_channels": ["email"],
    },
    "info": {
        "response_time_target": "Next business day",
        "update_frequency": "As needed",
        "requires_war_room": False,
        "auto_escalate": False,
        "notification_channels": [],
    },
}


def get_recommendations(
    incident_type: str,
    severity: str,
    title: str = "",
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Generate response recommendations for an incident.

    Args:
        incident_type: Classified incident type.
        severity: Incident severity level.
        title: Incident title for template rendering.
        context: Optional additional context.

    Returns:
        Dict with playbook, severity_response, and formatted recommendation.
    """
    playbook = PLAYBOOKS.get(incident_type, DEFAULT_PLAYBOOK)
    sev_response = SEVERITY_RESPONSE.get(severity, SEVERITY_RESPONSE["medium"])

    # Render communication template
    comm = playbook.get("communication_template", "Incident: {title}")
    try:
        comm = comm.format(title=title, eta="30 minutes", **(context or {}))
    except (KeyError, IndexError):
        comm = comm.replace("{title}", title)

    # Build formatted recommendation text
    rec_lines = [
        f"## Incident Response Plan",
        f"**Type:** {incident_type} | **Severity:** {severity}",
        f"**Response Target:** {sev_response['response_time_target']}",
        f"**Update Frequency:** {sev_response['update_frequency']}",
        "",
        "### Immediate Actions",
    ]
    for i, action in enumerate(playbook["immediate_actions"], 1):
        rec_lines.append(f"{i}. {action}")

    rec_lines.extend(["", "### Investigation Steps"])
    for i, step in enumerate(playbook["investigation_steps"], 1):
        rec_lines.append(f"{i}. {step}")

    if sev_response.get("requires_war_room"):
        rec_lines.extend(["", "⚠️ **War room required.** Gather all relevant engineers."])

    if sev_response.get("auto_escalate"):
        threshold = playbook.get("escalation_threshold_minutes", 30)
        rec_lines.extend(["", f"⏰ **Auto-escalation** if unresolved after {threshold} minutes."])

    return {
        "playbook": playbook,
        "severity_response": sev_response,
        "communication": comm,
        "recommendation_text": "\n".join(rec_lines),
        "escalation_threshold_minutes": playbook.get("escalation_threshold_minutes", 30),
        "notification_channels": sev_response.get("notification_channels", []),
    }

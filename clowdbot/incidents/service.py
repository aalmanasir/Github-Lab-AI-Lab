"""Incident lifecycle service - create, classify, recommend, resolve."""

from __future__ import annotations

import logging
from typing import Any

from clowdbot.database import (
    create_incident,
    get_incident,
    get_incident_stats,
    list_incidents,
    log_event,
    resolve_incident,
    update_incident,
)
from clowdbot.incidents.classifier import classify_incident, classify_with_ai
from clowdbot.incidents.recommender import get_recommendations
from clowdbot.monitoring.alerts import send_alert

logger = logging.getLogger(__name__)


class IncidentService:
    """High-level incident management service."""

    @staticmethod
    async def create(
        title: str,
        description: str | None = None,
        source: str = "manual",
        severity: str | None = None,
        incident_type: str | None = None,
        metadata: dict[str, Any] | None = None,
        use_ai: bool = False,
    ) -> dict[str, Any]:
        """Create a new incident with automatic classification and recommendations."""
        # Classify
        classification = classify_incident(title, description, source)

        # Try AI classification if requested
        ai_classification = None
        if use_ai:
            ai_classification = await classify_with_ai(title, description)
            if ai_classification and ai_classification.get("confidence", 0) > classification.get("confidence", 0):
                classification = ai_classification

        # Allow overrides
        final_type = incident_type or classification["incident_type"]
        final_severity = severity or classification["severity"]

        # Get recommendations
        recommendations = get_recommendations(final_type, final_severity, title)

        # Store
        incident_id = await create_incident(
            title=title,
            description=description,
            source=source,
            incident_type=final_type,
            severity=final_severity,
            metadata=metadata,
        )

        # Update with classification and recommendation
        await update_incident(
            incident_id,
            classification=str(classification),
            recommendation=recommendations["recommendation_text"],
        )

        # Log event
        await log_event(
            source="incidents",
            event_type="incident_created",
            summary=f"Incident #{incident_id}: {title}",
            severity=final_severity,
            metadata={"incident_id": incident_id, "type": final_type},
        )

        # Alert on critical/high
        if final_severity in ("critical", "high"):
            await send_alert(
                title=f"🚨 {final_severity.upper()} Incident: {title}",
                message=recommendations.get("communication", ""),
                severity=final_severity,
                fields=[
                    {"name": "Type", "value": final_type},
                    {"name": "Source", "value": source},
                    {"name": "Response Target", "value": recommendations["severity_response"]["response_time_target"]},
                ],
            )

        incident = await get_incident(incident_id)
        return {
            "incident": incident,
            "classification": classification,
            "recommendations": recommendations,
        }

    @staticmethod
    async def get(incident_id: int) -> dict[str, Any] | None:
        """Get incident by ID."""
        return await get_incident(incident_id)

    @staticmethod
    async def list_all(
        status: str | None = None,
        severity: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """List incidents with optional filters."""
        return await list_incidents(status=status, severity=severity, limit=limit, offset=offset)

    @staticmethod
    async def update(incident_id: int, **fields: Any) -> bool:
        """Update incident fields."""
        success = await update_incident(incident_id, **fields)
        if success:
            await log_event(
                source="incidents",
                event_type="incident_updated",
                summary=f"Incident #{incident_id} updated",
                severity="info",
                metadata={"incident_id": incident_id, "fields": list(fields.keys())},
            )
        return success

    @staticmethod
    async def resolve(incident_id: int, resolution: str, resolved_by: str) -> bool:
        """Resolve an incident."""
        success = await resolve_incident(incident_id, resolution, resolved_by)
        if success:
            incident = await get_incident(incident_id)
            await log_event(
                source="incidents",
                event_type="incident_resolved",
                summary=f"Incident #{incident_id} resolved by {resolved_by}",
                severity="info",
                metadata={"incident_id": incident_id, "resolution": resolution},
            )
            if incident:
                await send_alert(
                    title=f"✅ Incident Resolved: {incident.get('title', '')}",
                    message=f"Resolution: {resolution}\nResolved by: {resolved_by}",
                    severity="info",
                )
        return success

    @staticmethod
    async def stats() -> dict[str, Any]:
        """Get incident statistics."""
        return await get_incident_stats()

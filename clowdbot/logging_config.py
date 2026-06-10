"""Structured JSON logging configuration."""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any

__all__ = ["setup_logging"]


class JSONFormatter(logging.Formatter):
    """JSON log formatter with structured fields."""

    def format(self, record: logging.LogRecord) -> str:
        """Format a log record as JSON."""
        log_entry: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        if record.exc_info and record.exc_info[1] is not None:
            log_entry["exception"] = self.formatException(record.exc_info)

        # Include extra fields
        for key in ("source", "event_type", "severity", "user", "action"):
            if hasattr(record, key):
                log_entry[key] = getattr(record, key)

        return json.dumps(log_entry, default=str)


def setup_logging(level: str = "INFO") -> None:
    """Configure structured JSON logging for the application.

    Args:
        level: Log level string (DEBUG, INFO, WARNING, ERROR, CRITICAL).
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Clear existing handlers
    root_logger.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())
    root_logger.addHandler(handler)

    # Quiet noisy libraries
    logging.getLogger("aiosqlite").setLevel(logging.WARNING)
    logging.getLogger("discord").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

    logging.getLogger(__name__).info("Logging configured at %s level", level)

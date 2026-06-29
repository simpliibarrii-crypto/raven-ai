"""Audit gateway — every inference is logged.

Audit events are stored in FHIR AuditEvent-compatible JSON format.
In production, these would be exported to a FHIR server. For MVP,
we persist to a local append-only log.
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from pathlib import Path
from typing import Any

logger = logging.getLogger("openclinical.runtime.audit")


class AuditLogger:
    """Audit logger for clinical AI inferences.

    MVP: append-only JSON file. Production: FHIR AuditEvent export to server.
    """

    def __init__(self, audit_path: Path) -> None:
        self.audit_path = audit_path
        self.audit_path.mkdir(parents=True, exist_ok=True)
        self.log_file = self.audit_path / "audit.jsonl"
        self._lock = asyncio.Lock()

    async def log(self, **fields: Any) -> str:
        """Log an audit event and return the event ID."""
        event_id = str(uuid.uuid4())
        timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        event = {
            "event_id": event_id,
            "timestamp": timestamp,
            **fields,
        }

        async with self._lock:
            # MVP: append to file
            with open(self.log_file, "a") as f:
                f.write(json.dumps(event) + "\n")

        logger.info("audit event %s (%s)", event_id, fields.get("event_type", "unknown"))
        return event_id

    async def query(
        self,
        tenant_id: str | None = None,
        patient_id: str | None = None,
        model_id: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Query audit events with optional filters.

        tenant_id filter is mandatory for production — without it, callers
        see events from all tenants which would be a multi-tenant breach.
        """
        events = []
        if not self.log_file.exists():
            return events

        with open(self.log_file) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                event = json.loads(line)
                if tenant_id and event.get("tenant_id") != tenant_id:
                    continue
                if patient_id and event.get("patient_id") != patient_id:
                    continue
                if model_id and event.get("model_id") != model_id:
                    continue
                events.append(event)
                if len(events) >= limit:
                    break

        # Newest first
        return list(reversed(events))
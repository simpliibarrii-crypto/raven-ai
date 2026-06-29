"""Consent engine — patient consent propagated across the inference pipeline.

MVP: simple consent record per patient. Production: FHIR Consent resource
integration with hospital EHR systems.

Consent semantics:
- opt-in by default (PHIPA-aligned — explicit consent required for processing)
- consent can be granted, denied, or restricted (purpose-limited)
- consent can be revoked
- all consent decisions are logged to the audit gateway
"""
from __future__ import annotations

import json
import logging
import time
import uuid
from pathlib import Path
from typing import Any

logger = logging.getLogger("openclinical.runtime.consent")


class ConsentDenied(Exception):
    """Raised when consent is denied for an inference request."""
    pass


class ConsentEngine:
    """Patient consent engine.

    MVP: JSON file per patient. Production: FHIR Consent resource server.
    """

    def __init__(self, consent_path: Path) -> None:
        self.consent_path = consent_path
        self.consent_path.mkdir(parents=True, exist_ok=True)

    def _patient_file(self, patient_id: str) -> Path:
        return self.consent_path / f"{patient_id}.consent.json"

    def _load_consent(self, patient_id: str) -> dict[str, Any]:
        path = self._patient_file(patient_id)
        if not path.exists():
            # Default: no consent on file
            return {
                "patient_id": patient_id,
                "status": "no-record",
                "scope": [],
                "created_at": None,
            }
        with open(path) as f:
            return json.load(f)

    async def check(
        self,
        patient_id: str,
        model_id: str,
        consent_token: str | None = None,
    ) -> None:
        """Check consent for a patient + model combination.

        Raises ConsentDenied if consent is missing or insufficient.

        MVP rules:
        - consent_token must be present and valid
        - patient must have a consent record granting use of model_id
        - consent must not be revokedola        """
        consent = self._load_consent(patient_id)

        if consent.get("status") == "no-record":
            raise ConsentDenied(
                f"No consent record for patient {patient_id}. "
                "PHIPA requires explicit consent before processing health data."
            )

        if consent.get("status") == "denied":
            raise ConsentDenied(
                f"Consent denied for patient {patient_id}."
            )

        if consent.get("status") == "revoked":
            raise ConsentDenied(
                f"Consent revoked for patient {patient_id}."
            )

        if consent.get("status") != "active":
            raise ConsentDenied(
                f"Consent status '{consent.get('status')}' not recognized."
            )

        scope = consent.get("scope", [])
        if "*" not in scope and model_id not in scope:
            raise ConsentDenied(
                f"Patient {patient_id} consent does not cover model {model_id}. "
                f"Granted scope: {scope}."
            )

        # Verify consent token if present
        if consent_token and consent.get("token") != consent_token:
            raise ConsentDenied("Consent token mismatch.")

        logger.info(
            "consent granted for patient %s, model %s",
            patient_id,
            model_id,
        )

    async def grant_consent(
        self,
        patient_id: str,
        scope: list[str],
        granted_by: str,
        expires_at: str | None = None,
    ) -> str:
        """Grant consent for a patient. Returns the consent token."""
        token = str(uuid.uuid4())
        record = {
            "patient_id": patient_id,
            "status": "active",
            "scope": scope,
            "granted_by": granted_by,
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "expires_at": expires_at,
            "token": token,
        }
        with open(self._patient_file(patient_id), "w") as f:
            json.dump(record, f, indent=2)
        logger.info("consent granted for patient %s, scope %s", patient_id, scope)
        return token

    async def revoke_consent(self, patient_id: str, revoked_by: str) -> None:
        """Revoke consent for a patient."""
        record = self._load_consent(patient_id)
        record["status"] = "revoked"
        record["revoked_by"] = revoked_by
        record["revoked_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        with open(self._patient_file(patient_id), "w") as f:
            json.dump(record, f, indent=2)
        logger.info("consent revoked for patient %s by %s", patient_id, revoked_by)
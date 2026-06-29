"""Runtime configuration loaded from environment variables."""
from __future__ import annotations

import os
from pathlib import Path


class Settings:
    """Runtime settings — all overridable via environment variables."""

    def __init__(self) -> None:
        # Registry path — where signed models are stored
        self.registry_path = Path(
            os.getenv("OPENCLINICAL_REGISTRY_PATH", "/var/lib/openclinical/registry")
        )

        # Audit path — where audit events are persisted
        self.audit_path = Path(
            os.getenv("OPENCLINICAL_AUDIT_PATH", "/var/lib/openclinical/audit")
        )

        # Consent path — where consent records are persisted
        self.consent_path = Path(
            os.getenv("OPENCLINICAL_CONSENT_PATH", "/var/lib/openclinical/consent")
        )

        # Tenants path — multi-tenant registry
        self.tenants_path = Path(
            os.getenv("OPENCLINICAL_TENANTS_PATH", "/var/lib/openclinical/tenants")
        )

        # CORS — who can call the runtime from a browser
        cors_origins = os.getenv("OPENCLINICAL_CORS_ORIGINS", "*")
        self.allowed_origins = cors_origins.split(",") if cors_origins != "*" else ["*"]

        # Care plans path — per-tenant, per-facility structured care plans
        self.careplans_path = Path(
            os.getenv("OPENCLINICAL_CAREPLANS_PATH", "/var/lib/openclinical/careplans")
        )

        # FHIR base URL — for consent + audit FHIR resource lookups
        self.fhir_base_url = os.getenv("OPENCLINICAL_FHIR_BASE_URL", "")


settings = Settings()
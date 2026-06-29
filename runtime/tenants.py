"""Multi-tenant registry for openclinical-ai.

Each tenant is an isolated organization (home care agency, retirement home,
hospital, provincial health authority) that connects to openclinical-ai but
gets isolated cryptographic, audit, consent, and rate-limit boundaries.

Tenant types:
- agency-byok: tenant brings their own KMS key (best sovereignty)
- platform-managed: openclinical-ai holds the key (faster onboarding)
- shared: shared key (NOT recommended for healthcare — MVP/demo only)

Affordability tiers (see runtime.affordability):
- critical_access_rural, ltc_home, home_care_agency,
- regional_hospital, academic_medical_center,
- biotech_research, biotech_sovereign

In production, tenant records would live in a database. For MVP, JSON file.
"""
from __future__ import annotations

import json
import logging
import secrets
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger("openclinical.runtime.tenants")


@dataclass
class Tenant:
    """A tenant (organization) that connects to openclinical-ai."""
    id: str
    name: str
    encryption_model: str  # agency-byok | platform-managed | shared
    api_key_hash: str  # hashed — never store plaintext
    byok_key_ref: str | None = None  # KMS key reference if agency-byok
    contact_email: str = ""
    created_at: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    tier: str = "home_care_agency"  # affordability tier — see runtime.affordability


class TenantRegistry:
    """Registry of tenants. MVP: JSON file. Production: Postgres + caching."""

    def __init__(self, tenants_path: Path) -> None:
        self.tenants_path = tenants_path
        self.tenants_path.mkdir(parents=True, exist_ok=True)
        self.tenants: dict[str, Tenant] = {}
        self._api_key_to_tenant: dict[str, str] = {}  # api_key_hash -> tenant_id
        self._load()

    def _load(self) -> None:
        path = self.tenants_path / "tenants.json"
        if not path.exists():
            # Seed with demo tenants for MVP
            self._seed_demo_tenants()
            return
        with open(path) as f:
            data = json.load(f)
        for t in data.get("tenants", []):
            tenant = Tenant(**t)
            self.tenants[tenant.id] = tenant
            self._api_key_to_tenant[tenant.api_key_hash] = tenant.id

    def _save(self) -> None:
        path = self.tenants_path / "tenants.json"
        data = {"tenants": [t.__dict__ for t in self.tenants.values()]}
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    def _seed_demo_tenants(self) -> None:
        """Create demo tenants for local development — covers all tiers."""
        demo_tenants = [
            {
                "id": "bayshore-ottawa",
                "name": "Bayshore Home Health — Ottawa",
                "encryption_model": "agency-byok",
                "api_key_hash": self._hash_key("demo-bayshore-key"),
                "byok_key_ref": "aws-kms:arn:aws:kms:ca-central-1:111122223333:key/bayshore-ottawa",
                "contact_email": "ops-ottawa@bayshore.ca",
                "created_at": "2026-06-29T00:00:00Z",
                "metadata": {"province": "ON", "city": "Ottawa"},
                "tier": "home_care_agency",
            },
            {
                "id": "carefor-ottawa",
                "name": "Carefor Health & Community Services",
                "encryption_model": "agency-byok",
                "api_key_hash": self._hash_key("demo-carefor-key"),
                "byok_key_ref": "aws-kms:arn:aws:kms:ca-central-1:444455556666:key/carefor-ottawa",
                "contact_email": "it@carefor.ca",
                "created_at": "2026-06-29T00:00:00Z",
                "metadata": {"province": "ON", "city": "Ottawa"},
                "tier": "home_care_agency",
            },
            {
                "id": "vha-toronto",
                "name": "VHA Home HealthCare",
                "encryption_model": "platform-managed",
                "api_key_hash": self._hash_key("demo-vha-key"),
                "byok_key_ref": None,
                "contact_email": "tech@vha.ca",
                "created_at": "2026-06-29T00:00:00Z",
                "metadata": {"province": "ON", "city": "Toronto"},
                "tier": "home_care_agency",
            },
            {
                "id": "gary-j-armstrong",
                "name": "Garry J. Armstrong Retirement Home",
                "encryption_model": "agency-byok",
                "api_key_hash": self._hash_key("demo-armstrong-key"),
                "byok_key_ref": "aws-kms:arn:aws:kms:ca-central-1:777788889999:key/gary-j-armstrong",
                "contact_email": "admin@gjah.ca",
                "created_at": "2026-06-29T00:00:00Z",
                "metadata": {"province": "ON", "city": "Ottawa"},
                "tier": "ltc_home",
            },
            {
                "id": "toh-academic",
                "name": "The Ottawa Hospital — Academic",
                "encryption_model": "agency-byok",
                "api_key_hash": self._hash_key("demo-toh-key"),
                "byok_key_ref": "aws-kms:arn:aws:kms:ca-central-1:aaaabbbbcccc:key/toh-academic",
                "contact_email": "ai-research@toh.ca",
                "created_at": "2026-06-29T00:00:00Z",
                "metadata": {"province": "ON", "city": "Ottawa"},
                "tier": "academic_medical_center",
            },
        ]
        for t in demo_tenants:
            tenant = Tenant(**t)
            self.tenants[tenant.id] = tenant
            self._api_key_to_tenant[tenant.api_key_hash] = tenant.id
        self._save()
        logger.info("seeded %d demo tenants", len(self.tenants))

    @staticmethod
    def _hash_key(key: str) -> str:
        """Hash an API key for storage. Never store plaintext."""
        import hashlib
        return hashlib.sha256(key.encode()).hexdigest()

    def get(self, tenant_id: str) -> Tenant | None:
        return self.tenants.get(tenant_id)

    def get_by_api_key(self, api_key: str) -> Tenant | None:
        """Look up tenant by API key (hashed lookup)."""
        key_hash = self._hash_key(api_key)
        tenant_id = self._api_key_to_tenant.get(key_hash)
        if tenant_id:
            return self.tenants.get(tenant_id)
        return None

    def list(self) -> list[dict[str, Any]]:
        """List tenants (no secrets exposed)."""
        return [
            {
                "id": t.id,
                "name": t.name,
                "encryption_model": t.encryption_model,
                "tier": t.tier,
                "metadata": t.metadata,
            }
            for t in self.tenants.values()
        ]

    def create(
        self,
        name: str,
        encryption_model: str = "platform-managed",
        contact_email: str = "",
        metadata: dict[str, Any] | None = None,
        tier: str = "home_care_agency",
    ) -> tuple[Tenant, str]:
        """Create a new tenant + return (tenant, plaintext_api_key).

        The plaintext API key is shown ONCE to the admin — never stored.
        """
        tenant_id = name.lower().replace(" ", "-").replace("&", "and")[:50] + "-" + secrets.token_hex(3)
        api_key = secrets.token_urlsafe(32)

        tenant = Tenant(
            id=tenant_id,
            name=name,
            encryption_model=encryption_model,
            api_key_hash=self._hash_key(api_key),
            byok_key_ref=None,
            contact_email=contact_email,
            created_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            metadata=metadata or {},
            tier=tier,
        )

        self.tenants[tenant_id] = tenant
        self._api_key_to_tenant[tenant.api_key_hash] = tenant_id
        self._save()
        logger.info("created tenant %s (%s, tier=%s)", tenant_id, encryption_model, tier)
        return tenant, api_key
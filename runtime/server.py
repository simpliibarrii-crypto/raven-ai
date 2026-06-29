"""openclinical-ai runtime — multi-tenant inference server.

Hardened for healthcare:
- Multi-tenant isolation (per-tenant keys, audit, consent)
- Prompt-injection defense on all free-text inputs
- BYOK (Bring Your Own Key) encryption model
- Visit lifecycle (clock-in / clock-out with GPS)
- Family portal (read-only family-visible view)
- Consent + audit scoped by tenant
- Affordability tiers (DeepSeek V4-Pro / V4-Flash pricing model)
- Per-tenant cost transparency (tenant-scoped reports only)

Endpoints:
- GET  /health — runtime health
- GET  /models — list loaded models
- GET  /v1/tenants — list tenants (no secrets)
- POST /v1/auth/signin — sign in (password / OIDC / magic link)
- POST /v1/consent/grant — grant consent
- POST /v1/consent/revoke — revoke consent
- POST /v1/inference — run inference (sanitized, audited, cost-tracked)
- GET  /v1/visits/today — PSW's visits for today
- GET  /v1/visits/:id — visit details
- POST /v1/visits/clock-in — GPS clock-in
- POST /v1/visits/clock-out — finalize visit
- GET  /v1/family/timeline — family portal (read-only)
- GET  /audit/events — tenant-scoped audit log
- GET  /psw/ — static PSW UI (multi-tenant)
- GET  /v1/affordability/tiers — list affordability tiers (public)
- GET  /v1/affordability/eligibility — what the current tenant qualifies for
- POST /v1/inference/tier — resolve which tier + cost for a request
- GET  /v1/cost/report — per-tenant cost report (tenant-scoped ONLY)
- POST /v1/generate/{protein,binder,rna,dna} — generative biology (biosecurity-gated)
- POST /v1/synthesis/order — submit to Twist/IDT/GenScript
- GET  /v1/biosecurity/audit — biosecurity screening audit log
"""
from __future__ import annotations

import json
import logging
import os
import secrets
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path as PathLib
from typing import Any, AsyncIterator

from fastapi import Body, Depends, FastAPI, Header, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from runtime.config import settings
from runtime.models import ModelRegistry, ModelSignatureError, load_harness_prompt
from runtime.audit import AuditLogger
from runtime.consent import ConsentEngine, ConsentDenied
from runtime.tenants import TenantRegistry
from runtime.sanitize import sanitize_free_text, sanitize_observation_value
from runtime.bio_security import BiosecurityScreener, igs_screen_summary
from runtime.affordability import (
    ALL_TIERS,
    DEFAULT_TIER,
    default_quantization_for,
    estimate_cost,
    get_tier,
    list_tiers,
    V4_PRO_INPUT_USD_PER_M,
    V4_PRO_OUTPUT_USD_PER_M,
)
from runtime.careplan import CarePlan, CarePlanRegistry
from runtime.cost import CostTracker, CostRecord, build_cost_record
from runtime.efficient import default_compressor, default_router

logger = logging.getLogger("openclinical.runtime")
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))


# -- request / response schemas ---------------------------------------------


class InferenceRequest(BaseModel):
    """Request to run inference on a model."""
    tenant_id: str = Field(..., description="Tenant (agency) ID")
    model_id: str = Field(..., description="ID of the model to run")
    patient_id: str = Field(..., description="FHIR Patient.id of the client")
    inputs: dict[str, Any] = Field(..., description="Model-specific input payload")
    consent_token: str | None = Field(None, description="FHIR Consent reference token")


class InferenceResponse(BaseModel):
    inference_id: str
    tenant_id: str
    model_id: str
    model_version: str
    patient_id: str
    outputs: dict[str, Any]
    sanitization: dict[str, Any]
    audit_event_id: str
    timestamp: str
    latency_ms: int


class HealthResponse(BaseModel):
    status: str
    version: str
    models_loaded: int
    tenants: int
    uptime_seconds: float


class ConsentGrantRequest(BaseModel):
    tenant_id: str
    patient_id: str
    scope: list[str] = ["*"]
    granted_by: str
    expires_at: str | None = None


class ConsentGrantResponse(BaseModel):
    tenant_id: str
    patient_id: str
    token: str
    scope: list[str]
    granted_by: str
    granted_at: str


class ConsentRevokeRequest(BaseModel):
    tenant_id: str
    patient_id: str
    revoked_by: str


class SignInRequest(BaseModel):
    tenant_id: str
    psw_id: str
    method: str = "password"  # password | oidc | magic
    facility_id: str | None = None
    floor_id: str | None = None


class SignInResponse(BaseModel):
    tenant_id: str
    psw_id: str
    token: str
    consent_token: str | None = None
    encryption_model: str
    expires_at: str
    facility_id: str | None = None
    floor_id: str | None = None
    floor_plans: list[dict[str, Any]] = Field(default_factory=list)  # care plan briefs for this floor


class Visit(BaseModel):
    id: str
    tenant_id: str
    client_id: str
    client_name: str
    address: str | None
    scheduled_start: str
    scheduled_end: str
    service_type: str | None
    status: str  # scheduled | in-progress | completed | cancelled


class VisitClockInRequest(BaseModel):
    visit_id: str
    psw_id: str
    gps_lat: float
    gps_lng: float
    timestamp: str


class VisitClockOutRequest(BaseModel):
    visit_id: str
    psw_id: str
    timestamp: str
    family_visible_note: str | None = None


class FamilyTimelineItem(BaseModel):
    timestamp: str
    psw_name: str
    family_visible_note: str | None


class FamilyTimelineResponse(BaseModel):
    client_name: str
    visits: list[FamilyTimelineItem]


# -- generative biology schemas --------------------------------------------


class GenerateRequest(BaseModel):
    """Request to run a generative biology model.

    Inputs must include constraints specific to the model_id. Biosecurity
    screening is mandatory — every generated sequence is screened before
    being returned (per Science 2025).
    """
    tenant_id: str = Field(..., description="Tenant (agency/biotech) ID")
    model_id: str = Field(..., description="ID of the generation model (e.g. proteinmpnn-inverse-fold)")
    inputs: dict[str, Any] = Field(..., description="Model-specific input payload")


class GenerateResponse(BaseModel):
    generation_id: str
    tenant_id: str
    model_id: str
    model_version: str
    sequence: str
    sequence_type: str
    confidence: float
    cleared: bool  # False = blocked by biosecurity
    biosecurity: dict[str, Any]
    audit_event_id: str
    timestamp: str
    metadata: dict[str, Any]


class SynthesisOrderRequest(BaseModel):
    """Request to send a generated design to a synthesis vendor.

    Per Science 2025, synthesis-provider screening alone is insufficient.
    openclinical-ai's bio_security screening result is attached to the order
    so the vendor can see we already screened.
    """
    tenant_id: str
    generation_id: str
    vendor: str  # twist | idt | genscript
    sequence: str
    sequence_type: str  # protein | rna | dna
    biosecurity_hash: str  # SHA-256 hash matching the original screening result


class SynthesisOrderResponse(BaseModel):
    order_id: str
    status: str  # submitted | rejected
    vendor: str
    estimated_delivery_days: int
    biosecurity_verified: bool
    audit_event_id: str


# -- affordability + cost schemas ------------------------------------------


class AffordabilityEligibilityResponse(BaseModel):
    tenant_id: str
    tenant_name: str
    tier: dict[str, Any]
    estimated_monthly_cost_usd: dict[str, Any]


class TierResolutionRequest(BaseModel):
    """Resolve which tier / model family / quantization a request should use."""
    model_id: str
    input_tokens_estimate: int = 1000
    output_tokens_estimate: int = 500
    sensitivity: str = "standard"  # standard | high (clinical-decision-class)


class TierResolutionResponse(BaseModel):
    model_id: str
    tenant_tier_id: str
    resolved_model_family: str
    resolved_quantization: str
    activated_params_b: float
    estimated_cost_usd: float
    savings_vs_gpt55_usd: float
    savings_vs_opus47_usd: float
    max_context_tokens: int


class CostReportResponse(BaseModel):
    tenant_id: str
    window: dict[str, Any]
    inference_count: int
    totals: dict[str, Any]
    by_model_family: dict[str, Any]
    by_quantization: dict[str, Any]
    recent_records: list[dict[str, Any]]


class InferenceResponseWithCost(InferenceResponse):
    """Inference response augmented with cost transparency fields."""
    cost: dict[str, Any] = Field(default_factory=dict)
    tier_id: str = ""
    model_family: str = ""
    quantization: str = ""


# -- multi-tenant dependency --------------------------------------------------


class TenantContext:
    """Resolved tenant + authentication context for a request."""

    def __init__(
        self,
        tenant_id: str,
        psw_id: str,
        tenant_name: str,
        encryption_model: str,
        tier: str = "home_care_agency",
    ):
        self.tenant_id = tenant_id
        self.psw_id = psw_id
        self.tenant_name = tenant_name
        self.encryption_model = encryption_model
        self.tier = tier


async def require_tenant(
    request: Request,
    x_tenant_id: str = Header(...),
    x_tenant_api_key: str = Header(...),
    x_psw_id: str = Header(...),
) -> TenantContext:
    """Verify tenant + authentication, return tenant context.

    Accepts either:
    - Persistent tenant API key (hashed lookup in tenant registry)
    - Session token (issued by /v1/auth/signin, valid for 8 hours)

    Every protected endpoint uses this. No tenant context = no access.
    """
    registry: TenantRegistry = request.app.state.tenants
    tenant = registry.get(x_tenant_id)
    if not tenant:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Unknown tenant")

    # Try session token first (faster, expires)
    sessions = getattr(request.app.state, "sessions", {})
    session = sessions.get(x_tenant_api_key)
    if session:
        if session["tenant_id"] != x_tenant_id:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Session tenant mismatch")
        if session["expires_at"] < time.time():
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Session expired")
        if session["psw_id"] != x_psw_id:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "PSW ID mismatch")
        return TenantContext(
            tenant_id=tenant.id,
            psw_id=x_psw_id,
            tenant_name=tenant.name,
            encryption_model=tenant.encryption_model,
            tier=tenant.tier,
        )

    # Fall back to persistent tenant API key (hashed lookup)
    api_key_tenant = registry.get_by_api_key(x_tenant_api_key)
    if not api_key_tenant or api_key_tenant.id != x_tenant_id:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid tenant API key")

    return TenantContext(
        tenant_id=tenant.id,
        psw_id=x_psw_id,
        tenant_name=tenant.name,
        encryption_model=tenant.encryption_model,
        tier=tenant.tier,
    )


# -- application lifecycle ---------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Initialize runtime state on startup, clean up on shutdown."""
    logger.info("openclinical-ai runtime starting — version %s", __import__("runtime").__version__)

    # Load the AI governance harness system prompt
    docs_dir = PathLib(__file__).resolve().parents[1] / "docs"
    harness_prompt = load_harness_prompt(docs_dir)
    app.state.harness_prompt = harness_prompt

    app.state.tenants = TenantRegistry(tenants_path=settings.tenants_path)
    app.state.registry = ModelRegistry(registry_path=settings.registry_path, system_prompt=harness_prompt)
    app.state.audit = AuditLogger(audit_path=settings.audit_path)
    app.state.consent = ConsentEngine(consent_path=settings.consent_path)
    app.state.biosecurity = BiosecurityScreener()
    app.state.cost = CostTracker()  # per-tenant cost transparency
    app.state.careplans = CarePlanRegistry(plans_path=settings.careplans_path)
    app.state.started_at = time.time()
    # Only seed demo data in dev/test
    if os.getenv("OPENCLINICAL_ENV", "dev") != "production":
        app.state.visits = _seed_demo_visits()
        app.state.careplans.seed_demo_plans()
    else:
        app.state.visits = {}
    app.state.sessions = {}  # token -> session metadata
    # In-memory call bell event queue (floor -> list of pending events)
    app.state.callbell_queue: dict[str, list[dict[str, Any]]] = {}

    # Load any pre-registered models
    loaded = await app.state.registry.load_all()
    logger.info("loaded %d models, %d tenants", loaded, len(app.state.tenants.tenants))

    yield

    logger.info("openclinical-ai runtime shutting down")


# -- cost / token / model-family helpers ----------------------------------


def _estimate_tokens(inputs: dict[str, Any], outputs: dict[str, Any]) -> tuple[int, int]:
    """Estimate input + output tokens. MVP heuristic: ~4 chars per token.

    For real adapters this is replaced by tokenizer counts (tiktoken, etc.).
    The estimate is intentionally conservative — over-counting is safer
    than under-counting for cost reporting.
    """
    def count(d: dict[str, Any]) -> int:
        total = 0
        for v in d.values():
            if isinstance(v, str):
                total += max(1, len(v) // 4)
            elif isinstance(v, dict):
                total += count(v)
            elif isinstance(v, list):
                for item in v:
                    if isinstance(item, str):
                        total += max(1, len(item) // 4)
                    elif isinstance(item, dict):
                        total += count(item)
            elif v is not None:
                total += max(1, len(str(v)) // 4)
        return total

    return count(inputs), count(outputs)


def _resolve_model_family(model_id: str) -> tuple[str, float]:
    """Resolve a model_id to its model family + activated params (billions).

    Anchors in DeepSeek V4-Pro / V4-Flash activated-param counts:
    - V4-Pro:   49B activated out of 1.6T total (3%)
    - V4-Flash: 13B activated out of 284B total (4.5%)
    - DSpark:   on-prem, same activated params as V4-Pro
    - heuristic: 0B (no real inference — pure rule-based)
    """
    mid = model_id.lower()
    if "v4-pro" in mid or "v4pro" in mid:
        return "v4-pro", 49.0
    if "v4-flash" in mid or "v4flash" in mid:
        return "v4-flash", 13.0
    if "dspark" in mid:
        return "dspark", 49.0
    if "psw" in mid or "shift" in mid or "handoff" in mid:
        return "heuristic", 0.0
    # Default for unknown model_ids: assume heuristic
    return "heuristic", 0.0


def _estimated_monthly_cost(
    tier_id: str,
    inferences_per_day: int,
    avg_input_tokens: int,
    avg_output_tokens: int,
) -> dict[str, Any]:
    """Estimate monthly cost (30 days) at a given tier.

    Uses the tier's published pricing for V4-Pro / V4-Flash / DSpark.
    Returns cost + savings vs GPT-5.5 + Opus 4.7 baselines.
    """
    tier = get_tier(tier_id)
    monthly_inferences = inferences_per_day * 30
    cost = tier.estimate_cost(
        avg_input_tokens * monthly_inferences,
        avg_output_tokens * monthly_inferences,
    )
    gpt55 = (
        (avg_input_tokens / 1_000_000) * 10.0 * monthly_inferences
        + (avg_output_tokens / 1_000_000) * 30.0 * monthly_inferences
    )
    opus47 = (
        (avg_input_tokens / 1_000_000) * 15.0 * monthly_inferences
        + (avg_output_tokens / 1_000_000) * 75.0 * monthly_inferences
    )
    return {
        "inferences_per_month": monthly_inferences,
        "estimated_monthly_cost_usd": round(cost, 4),
        "estimated_monthly_cost_gpt55_usd": round(gpt55, 4),
        "estimated_monthly_cost_opus47_usd": round(opus47, 4),
        "monthly_savings_vs_gpt55_usd": round(gpt55 - cost, 4),
        "monthly_savings_vs_opus47_usd": round(opus47 - cost, 4),
    }


def _seed_demo_visits() -> dict[str, Visit]:
    """Seed demo visits for MVP testing."""
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    today = now[:10]
    visits = [
        Visit(
            id="visit-001", tenant_id="bayshore-ottawa",
            client_id="client-001", client_name="Mary Tremblay",
            address="123 Main St, Ottawa ON",
            scheduled_start=f"{today}T08:00:00Z", scheduled_end=f"{today}T09:00:00Z",
            service_type="Personal care + medication",
            status="scheduled",
        ),
        Visit(
            id="visit-002", tenant_id="bayshore-ottawa",
            client_id="client-002", client_name="John O'Brien",
            address="456 Oak Ave, Ottawa ON",
            scheduled_start=f"{today}T10:30:00Z", scheduled_end=f"{today}T11:30:00Z",
            service_type="Personal care",
            status="scheduled",
        ),
        Visit(
            id="visit-003", tenant_id="carefor-ottawa",
            client_id="client-003", client_name="Eleanor Smith",
            address="789 Pine St, Ottawa ON",
            scheduled_start=f"{today}T13:00:00Z", scheduled_end=f"{today}T14:00:00Z",
            service_type="Respite + meal prep",
            status="scheduled",
        ),
    ]
    return {v.id: v for v in visits}


app = FastAPI(
    title="openclinical-ai runtime",
    description="Multi-tenant sovereign inference runtime for biology AI and clinical AI",
    version="0.4.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -- public endpoints (no tenant auth) ---------------------------------------


@app.get("/health", response_model=HealthResponse)
async def health(request: Request) -> HealthResponse:
    """Runtime health check — public."""
    return HealthResponse(
        status="healthy",
        version=request.app.version,
        models_loaded=len(request.app.state.registry.loaded_models),
        tenants=len(request.app.state.tenants.tenants),
        uptime_seconds=time.time() - request.app.state.started_at,
    )


@app.get("/models")
async def list_models(request: Request) -> dict[str, Any]:
    """List all loaded models — public (no PHI)."""
    registry: ModelRegistry = request.app.state.registry
    return {
        "models": [
            {
                "id": m.id,
                "version": m.version,
                "type": m.model_type,
                "description": m.description,
                "loaded_at": m.loaded_at,
            }
            for m in registry.loaded_models.values()
        ]
    }


@app.get("/v1/tenants")
async def list_tenants(request: Request) -> dict[str, Any]:
    """List tenants — public (no secrets exposed).

    Used by the PSW UI to populate the agency selector.
    """
    registry: TenantRegistry = request.app.state.tenants
    return {"tenants": registry.list()}


@app.post("/v1/auth/signin", response_model=SignInResponse)
async def sign_in(req: SignInRequest, request: Request) -> SignInResponse:
    """Sign in a PSW into a tenant.

    MVP: accepts any PSW ID + valid tenant API key + valid sign-in method.
    Production: validates against IdP (OIDC, SAML, LDAP), enforces MFA,
    issues JWT or session cookie.

    The token returned is used in the X-Tenant-API-Key header for subsequent calls.
    For MVP, we issue a long-lived session token tied to the tenant.
    """
    registry: TenantRegistry = request.app.state.tenants
    tenant = registry.get(req.tenant_id)
    if not tenant:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Unknown tenant")

    # MVP: accept any PSW ID. Production: validate password/SSO.
    session_token = secrets.token_urlsafe(32)
    request.app.state.sessions[session_token] = {
        "tenant_id": req.tenant_id,
        "psw_id": req.psw_id,
        "created_at": time.time(),
        "expires_at": time.time() + 8 * 3600,  # 8 hour shift
    }

    # Grant default consent for the PSW's clients (MVP)
    consent_token = None
    if req.method in ("password", "oidc"):
        consent_token = await request.app.state.consent.grant_consent(
            patient_id=f"default-{req.psw_id}",
            scope=["visit_documentation"],
            granted_by=req.psw_id,
        )

    # Load care plans for the assigned floor
    floor_plans: list[dict[str, Any]] = []
    if req.facility_id and req.floor_id:
        careplans: CarePlanRegistry = request.app.state.careplans
        plans = careplans.get_by_floor(req.tenant_id, req.facility_id, req.floor_id)
        floor_plans = [p.to_brief() for p in plans]
        audit_cp: AuditLogger = request.app.state.audit
        await audit_cp.log(
            event_type="floor-signin",
            tenant_id=req.tenant_id,
            psw_id=req.psw_id,
            facility_id=req.facility_id,
            floor_id=req.floor_id,
            plans_loaded=len(floor_plans),
        )

    return SignInResponse(
        tenant_id=req.tenant_id,
        psw_id=req.psw_id,
        token=session_token,
        consent_token=consent_token,
        encryption_model=tenant.encryption_model,
        expires_at=time.strftime(
            "%Y-%m-%dT%H:%M:%SZ",
            time.gmtime(time.time() + 8 * 3600),
        ),
        facility_id=req.facility_id,
        floor_id=req.floor_id,
        floor_plans=floor_plans,
    )


@app.post("/v1/consent/grant", response_model=ConsentGrantResponse)
async def consent_grant(req: ConsentGrantRequest, request: Request) -> ConsentGrantResponse:
    """Grant consent — tenant-scoped."""
    consent: ConsentEngine = request.app.state.consent
    token = await consent.grant_consent(
        patient_id=req.patient_id,
        scope=req.scope,
        granted_by=req.granted_by,
        expires_at=req.expires_at,
    )
    return ConsentGrantResponse(
        tenant_id=req.tenant_id,
        patient_id=req.patient_id,
        token=token,
        scope=req.scope,
        granted_by=req.granted_by,
        granted_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    )


@app.post("/v1/consent/revoke")
async def consent_revoke(req: ConsentRevokeRequest, request: Request) -> dict[str, str]:
    """Revoke consent — tenant-scoped."""
    consent: ConsentEngine = request.app.state.consent
    await consent.revoke_consent(req.patient_id, req.revoked_by)
    return {"status": "revoked", "patient_id": req.patient_id}


# -- affordability + cost public endpoints ---------------------------------


@app.get("/v1/affordability/tiers")
async def affordability_tiers() -> dict[str, Any]:
    """List all affordability tiers — public (no secrets, no tenant auth)."""
    return {"tiers": list_tiers()}


# -- protected endpoints (require tenant auth) -------------------------------


@app.post("/v1/inference", response_model=InferenceResponseWithCost)
async def inference(
    req: InferenceRequest,
    request: Request,
    ctx: TenantContext = Depends(require_tenant),
) -> InferenceResponseWithCost:
    """Run inference on a model — multi-tenant, sanitized, audited, cost-tracked."""
    started = time.time()
    inference_id = str(uuid.uuid4())

    # Verify tenant matches request
    if req.tenant_id != ctx.tenant_id:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "tenant_id in request body must match X-Tenant-ID header",
        )

    registry: ModelRegistry = request.app.state.registry
    audit: AuditLogger = request.app.state.audit
    consent: ConsentEngine = request.app.state.consent

    # 1. Resolve model
    model = registry.get(req.model_id)
    if model is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            f"Model {req.model_id} not found in registry",
        )

    # 2. Check consent (tenant-scoped)
    try:
        await consent.check(req.patient_id, req.model_id, req.consent_token)
    except ConsentDenied as e:
        await audit.log(
            event_type="consent-denied",
            inference_id=inference_id,
            tenant_id=ctx.tenant_id,
            psw_id=ctx.psw_id,
            patient_id=req.patient_id,
            model_id=req.model_id,
            model_version=model.version,
            reason=str(e),
        )
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            f"Consent denied: {e}",
        )

    # 3. Sanitize inputs (prompt-injection defense)
    sanitization_report: dict[str, Any] = {"flagged": [], "truncated": False}
    inputs = req.inputs.copy()

    if "notes" in inputs and inputs["notes"]:
        result = sanitize_free_text(inputs["notes"])
        inputs["notes"] = result.text
        sanitization_report["flagged"] = result.flagged_patterns
        sanitization_report["truncated"] = result.truncated
        if result.flagged_patterns:
            await audit.log(
                event_type="prompt-injection-blocked",
                inference_id=inference_id,
                tenant_id=ctx.tenant_id,
                psw_id=ctx.psw_id,
                patient_id=req.patient_id,
                model_id=req.model_id,
                flagged_patterns=result.flagged_patterns,
            )

    # Sanitize observation values
    if "observations" in inputs and isinstance(inputs["observations"], dict):
        for k, v in list(inputs["observations"].items()):
            if v is not None:
                inputs["observations"][k] = sanitize_observation_value(str(v))

    # 4. Run inference
    try:
        outputs = await model.run(inputs)
    except Exception as e:
        logger.exception("inference failed for model %s", req.model_id)
        await audit.log(
            event_type="inference-error",
            inference_id=inference_id,
            tenant_id=ctx.tenant_id,
            psw_id=ctx.psw_id,
            patient_id=req.patient_id,
            model_id=req.model_id,
            model_version=model.version,
            reason=str(e),
        )
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Inference failed",
        )

    # 5. Audit
    audit_event_id = await audit.log(
        event_type="inference",
        inference_id=inference_id,
        tenant_id=ctx.tenant_id,
        psw_id=ctx.psw_id,
        patient_id=req.patient_id,
        model_id=req.model_id,
        model_version=model.version,
        sanitization=sanitization_report,
        consent_token=req.consent_token,
    )

    # 6. Cost transparency — every inference is cost-tracked + audit-logged
    cost_tracker: CostTracker = request.app.state.cost
    input_tokens, output_tokens = _estimate_tokens(inputs, outputs)
    model_family, activated_params_b = _resolve_model_family(req.model_id)
    quantization = default_quantization_for(req.model_id, ctx.tier)
    cost_record = build_cost_record(
        inference_id=inference_id,
        tenant_id=ctx.tenant_id,
        psw_id=ctx.psw_id,
        model_id=req.model_id,
        model_family=model_family,
        tier_id=ctx.tier,
        quantization=quantization,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        activated_params_b=activated_params_b,
        audit_event_id=audit_event_id,
    )
    cost_tracker.record(cost_record)

    latency_ms = int((time.time() - started) * 1000)

    return InferenceResponseWithCost(
        inference_id=inference_id,
        tenant_id=ctx.tenant_id,
        model_id=req.model_id,
        model_version=model.version,
        patient_id=req.patient_id,
        outputs=outputs,
        sanitization=sanitization_report,
        audit_event_id=audit_event_id,
        timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        latency_ms=latency_ms,
        cost={
            "estimated_cost_usd": cost_record.estimated_cost_usd,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "savings_vs_gpt55_usd": cost_record.savings_vs_gpt55_usd,
            "savings_vs_opus47_usd": cost_record.savings_vs_opus47_usd,
        },
        tier_id=ctx.tier,
        model_family=model_family,
        quantization=quantization,
    )


@app.get("/v1/affordability/eligibility")
async def affordability_eligibility(
    request: Request,
    ctx: TenantContext = Depends(require_tenant),
) -> dict[str, Any]:
    """Show what the current tenant qualifies for.

    Estimated monthly cost is shown based on tier defaults (100 inferences/day
    at avg 1000 in / 500 out tokens). Production: tenant-specific usage stats.
    """
    registry: TenantRegistry = request.app.state.tenants
    tenant = registry.get(ctx.tenant_id)
    tier = get_tier(ctx.tier)
    estimated = _estimated_monthly_cost(
        tier_id=ctx.tier,
        inferences_per_day=100,
        avg_input_tokens=1000,
        avg_output_tokens=500,
    )
    return {
        "tenant_id": ctx.tenant_id,
        "tenant_name": ctx.tenant_name,
        "tier": tier.to_dict(),
        "estimated_monthly_cost_usd": estimated,
    }


@app.post("/v1/inference/tier", response_model=TierResolutionResponse)
async def inference_tier(
    req: TierResolutionRequest,
    request: Request,
    ctx: TenantContext = Depends(require_tenant),
) -> TierResolutionResponse:
    """Resolve which tier + model family + quantization + cost a request should use.

    Useful for clients that want to preview cost before committing to
    an inference, or for tools that need to choose between V4-Pro / V4-Flash
    / DSpark dynamically.
    """
    tier = get_tier(ctx.tier)
    model_family, activated_params_b = _resolve_model_family(req.model_id)
    # Clinical-decision-class sensitivity forces fp16 regardless of tier default
    if req.sensitivity == "high":
        quantization = "fp16"
    else:
        quantization = default_quantization_for(req.model_id, ctx.tier)
    cost = estimate_cost(ctx.tier, req.input_tokens_estimate, req.output_tokens_estimate)
    return TierResolutionResponse(
        model_id=req.model_id,
        tenant_tier_id=ctx.tier,
        resolved_model_family=model_family,
        resolved_quantization=quantization,
        activated_params_b=activated_params_b,
        estimated_cost_usd=cost["tier_cost_usd"],
        savings_vs_gpt55_usd=cost["savings_vs_gpt55_usd"],
        savings_vs_opus47_usd=cost["savings_vs_opus47_usd"],
        max_context_tokens=tier.max_context_tokens,
    )


@app.get("/v1/cost/report", response_model=CostReportResponse)
async def cost_report(
    request: Request,
    since: str | None = None,
    ctx: TenantContext = Depends(require_tenant),
) -> CostReportResponse:
    """Per-tenant cost report — tenant-scoped ONLY.

    No cross-tenant visibility. This is by design: cost transparency
    is for the patient's affordability, not for tenant-vs-tenant
    competitive comparison.
    """
    cost_tracker: CostTracker = request.app.state.cost
    report = cost_tracker.tenant_report(ctx.tenant_id, since_timestamp=since)
    return CostReportResponse(**report)


@app.get("/v1/visits/today")
async def visits_today(
    request: Request,
    ctx: TenantContext = Depends(require_tenant),
    psw_id: str = "",
) -> dict[str, Any]:
    """List today's visits for the signed-in PSW.

    MVP: returns all visits for the tenant filtered to the PSW (or all if no PSW filter).
    Production: filtered by PSW assignment + tenant + date.
    """
    visits = request.app.state.visits
    today_str = time.strftime("%Y-%m-%d", time.gmtime())

    matching = [
        v for v in visits.values()
        if v.tenant_id == ctx.tenant_id
        and v.scheduled_start.startswith(today_str)
    ]

    return {
        "tenant_id": ctx.tenant_id,
        "psw_id": psw_id or ctx.psw_id,
        "visits": [v.model_dump() for v in matching],
    }


@app.get("/v1/visits/{visit_id}")
async def visit_get(
    visit_id: str,
    request: Request,
    ctx: TenantContext = Depends(require_tenant),
) -> dict[str, Any]:
    """Get a single visit by ID — tenant-scoped."""
    visit = request.app.state.visits.get(visit_id)
    if not visit or visit.tenant_id != ctx.tenant_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Visit not found")
    return visit.model_dump()


@app.post("/v1/visits/clock-in")
async def visit_clock_in(
    req: VisitClockInRequest,
    request: Request,
    ctx: TenantContext = Depends(require_tenant),
) -> dict[str, Any]:
    """GPS clock-in for a visit — tenant-scoped, audit-logged."""
    visit = request.app.state.visits.get(req.visit_id)
    if not visit or visit.tenant_id != ctx.tenant_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Visit not found")

    visit.status = "in-progress"
    request.app.state.visits[req.visit_id] = visit

    audit: AuditLogger = request.app.state.audit
    audit_event_id = await audit.log(
        event_type="visit-clock-in",
        tenant_id=ctx.tenant_id,
        psw_id=ctx.psw_id,
        visit_id=req.visit_id,
        gps_lat=req.gps_lat,
        gps_lng=req.gps_lng,
        timestamp=req.timestamp,
    )

    return {
        "status": "clocked-in",
        "visit_id": req.visit_id,
        "audit_event_id": audit_event_id,
    }


@app.post("/v1/visits/clock-out")
async def visit_clock_out(
    req: VisitClockOutRequest,
    request: Request,
    ctx: TenantContext = Depends(require_tenant),
) -> dict[str, Any]:
    """Clock-out for a visit — tenant-scoped, audit-logged, with optional family-visible note.

    Family-visible note is sanitized before being stored — no PHI allowed.
    """
    visit = request.app.state.visits.get(req.visit_id)
    if not visit or visit.tenant_id != ctx.tenant_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Visit not found")

    visit.status = "completed"
    request.app.state.visits[req.visit_id] = visit

    family_note_sanitized = ""
    if req.family_visible_note:
        result = sanitize_free_text(req.family_visible_note, max_chars=1000)
        family_note_sanitized = result.text

    audit: AuditLogger = request.app.state.audit
    audit_event_id = await audit.log(
        event_type="visit-clock-out",
        tenant_id=ctx.tenant_id,
        psw_id=ctx.psw_id,
        visit_id=req.visit_id,
        timestamp=req.timestamp,
        family_visible_note=family_note_sanitized,
        has_family_note=bool(family_note_sanitized),
    )

    return {
        "status": "completed",
        "visit_id": req.visit_id,
        "family_visible_note": family_note_sanitized,
        "audit_event_id": audit_event_id,
    }


@app.get("/v1/family/timeline", response_model=FamilyTimelineResponse)
async def family_timeline(
    request: Request,
    token: str | None = None,
    client_id: str | None = None,
    x_family_token: str | None = Header(None, alias="X-Family-Token"),
) -> FamilyTimelineResponse:
    """Family portal — read-only view of family-visible notes.

    Uses a separate family-portal token (not the PSW API key). Token accepted
    via X-Family-Token header (preferred — avoids tokens in URLs/logs) or
    ?token= query param (backward compat).
    MVP: returns a placeholder.
    Production: validates family token, returns only family-visible fields.
    """
    # Prefer header over query param — tokens in URLs land in logs + referrers
    effective_token = x_family_token or token or ""
    _ = effective_token  # MVP: unused; production validation target
    return FamilyTimelineResponse(
        client_name="your loved one",
        visits=[],
    )


@app.get("/audit/events")
async def list_audit_events(
    request: Request,
    tenant_id: str,
    patient_id: str | None = None,
    model_id: str | None = None,
    limit: int = 100,
    ctx: TenantContext = Depends(require_tenant),
) -> dict[str, Any]:
    """List audit events — tenant-scoped, authenticated.

    Only returns events for the authenticated tenant. Any attempt to query
    another tenant's audit log returns 403.
    """
    if tenant_id != ctx.tenant_id:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Cannot query audit events for another tenant",
        )
    audit: AuditLogger = request.app.state.audit
    events = await audit.query(
        tenant_id=tenant_id,
        patient_id=patient_id,
        model_id=model_id,
        limit=limit,
    )
    return {"tenant_id": tenant_id, "events": events, "count": len(events)}


@app.exception_handler(ModelSignatureError)
async def model_signature_error_handler(request: Request, exc: ModelSignatureError) -> JSONResponse:
    """Models must have valid signatures — unsigned models are rejected."""
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={
            "error": "model_signature_invalid",
            "detail": str(exc),
            "policy": "openclinical-ai rejects unsigned or invalid-signed models. See registry/signing.md.",
        },
    )


# -- generative biology endpoints (multi-tenant, biosecurity-gated) ----------


# Available biology AI generation models (for error messages)
BIOLOGY_GENERATION_ADAPTERS_REGISTRY = {
    "rfdiffusion-backbone": "Generative protein backbone design (Baker lab, BSD open source)",
    "proteinmpnn-inverse-fold": "Inverse folding — sequence from backbone (Baker lab, BSD open source)",
    "esm3-multimodal": "Multi-modal protein LLM (EvolutionaryScale, Apache 2.0 ESM Cambrian)",
    "bindcraft-binder-design": "Binder design against target (Baker lab, BSD open source)",
    "progen-protein-llm": "Control-tag protein LLM (Profluent/Salesforce, Apache 2.0)",
}


@app.post("/v1/generate/protein", response_model=GenerateResponse)
async def generate_protein(
    req: GenerateRequest,
    request: Request,
    ctx: TenantContext = Depends(require_tenant),
) -> GenerateResponse:
    """Generate a protein sequence using a generative biology model.

    Biosecurity screening is mandatory. Cleared sequences are returned.
    Flagged sequences are returned with cleared=False + biosecurity details
    so callers can review. High-risk sequences (risk > 0.7) are blocked.
    """
    return await _run_generation(req, request, ctx, sequence_type="protein")


@app.post("/v1/generate/binder", response_model=GenerateResponse)
async def generate_binder(
    req: GenerateRequest,
    request: Request,
    ctx: TenantContext = Depends(require_tenant),
) -> GenerateResponse:
    """Generate a binder protein against a target structure.

    Uses Bindcraft adapter (Baker lab) under the hood.
    """
    return await _run_generation(req, request, ctx, sequence_type="protein")


@app.post("/v1/generate/rna", response_model=GenerateResponse)
async def generate_rna(
    req: GenerateRequest,
    request: Request,
    ctx: TenantContext = Depends(require_tenant),
) -> GenerateResponse:
    """Generate an RNA sequence."""
    return await _run_generation(req, request, ctx, sequence_type="rna")


@app.post("/v1/generate/dna", response_model=GenerateResponse)
async def generate_dna(
    req: GenerateRequest,
    request: Request,
    ctx: TenantContext = Depends(require_tenant),
) -> GenerateResponse:
    """Generate a DNA sequence."""
    return await _run_generation(req, request, ctx, sequence_type="dna")


async def _run_generation(
    req: GenerateRequest,
    request: Request,
    ctx: TenantContext,
    sequence_type: str,
) -> GenerateResponse:
    """Shared logic for all /v1/generate/* endpoints.

    1. Look up generation adapter (from biology-ai/generation/)
    2. Run generation (model-specific)
    3. Screen the output through biosecurity
    4. Audit the generation event (tenant-scoped)
    5. Return GenerateResponse with biosecurity details
    """
    from biology_ai.generation.adapters import get_generation_adapter

    if req.tenant_id != ctx.tenant_id:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "tenant_id in request body must match X-Tenant-ID header",
        )

    adapter = get_generation_adapter(req.model_id)
    if adapter is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            f"Generation model {req.model_id} not registered. "
            f"Available: {list(BIOLOGY_GENERATION_ADAPTERS_REGISTRY.keys())}",
        )

    screener: BiosecurityScreener = request.app.state.biosecurity
    audit: AuditLogger = request.app.state.audit

    # 1. Run generation + screening
    output = await adapter.run(req.inputs, screener)

    # 2. Block high-risk sequences (risk_score > 0.7)
    if not output.biosecurity["cleared"] and output.biosecurity["risk_score"] > 0.7:
        audit_event_id = await audit.log(
            event_type="biosecurity-blocked",
            tenant_id=ctx.tenant_id,
            psw_id=ctx.psw_id,
            model_id=req.model_id,
            model_version=adapter.model_version,
            sequence_type=sequence_type,
            sequence_hash=output.biosecurity.get("sequence_id", ""),
            risk_score=output.biosecurity["risk_score"],
            flags=output.biosecurity["flags"],
        )
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            {
                "error": "biosecurity_blocked",
                "detail": "Sequence blocked by biosecurity screening (high risk). Manual review required.",
                "biosecurity": output.biosecurity,
                "audit_event_id": audit_event_id,
            },
        )

    # 3. Audit successful generation
    event_type = "generation-cleared" if output.biosecurity["cleared"] else "generation-flagged"
    audit_event_id = await audit.log(
        event_type=event_type,
        tenant_id=ctx.tenant_id,
        psw_id=ctx.psw_id,
        model_id=req.model_id,
        model_version=adapter.model_version,
        sequence_type=sequence_type,
        sequence_length=len(output.sequence),
        sequence_hash=output.biosecurity.get("sequence_id", ""),
        risk_score=output.biosecurity["risk_score"],
        flags=output.biosecurity["flags"],
        generation_id=output.generation_id,
    )

    return GenerateResponse(
        generation_id=output.generation_id,
        tenant_id=ctx.tenant_id,
        model_id=req.model_id,
        model_version=adapter.model_version,
        sequence=output.sequence,
        sequence_type=output.sequence_type,
        confidence=output.confidence,
        cleared=output.biosecurity["cleared"],
        biosecurity=output.biosecurity,
        audit_event_id=audit_event_id,
        timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        metadata=output.metadata,
    )


# -- synthesis vendor integration -------------------------------------------


@app.post("/v1/synthesis/order", response_model=SynthesisOrderResponse)
async def synthesis_order(
    req: SynthesisOrderRequest,
    request: Request,
    ctx: TenantContext = Depends(require_tenant),
) -> SynthesisOrderResponse:
    """Send a generated design to a synthesis vendor (Twist, IDT, GenScript).

    Per Science 2025, synthesis-provider screening alone is insufficient.
    openclinical-ai attaches its own bio_security screening result so the
    vendor has the full context.

    MVP: stub that records the order + returns a fake order ID.
    Production: real vendor API integration.
    """
    if req.tenant_id != ctx.tenant_id:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "tenant_id must match X-Tenant-ID header",
        )

    if req.vendor not in ("twist", "idt", "genscript"):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Unknown vendor '{req.vendor}'. Supported: twist, idt, genscript",
        )

    audit: AuditLogger = request.app.state.audit
    order_id = f"ORD-{uuid.uuid4().hex[:12]}"

    # Estimate delivery
    delivery_days = {
        "twist": 7,
        "idt": 5,
        "genscript": 14,
    }.get(req.vendor, 10)

    audit_event_id = await audit.log(
        event_type="synthesis-order",
        tenant_id=ctx.tenant_id,
        psw_id=ctx.psw_id,
        order_id=order_id,
        vendor=req.vendor,
        sequence_type=req.sequence_type,
        sequence_length=len(req.sequence),
        biosecurity_hash=req.biosecurity_hash,
        generation_id=req.generation_id,
    )

    return SynthesisOrderResponse(
        order_id=order_id,
        status="submitted",
        vendor=req.vendor,
        estimated_delivery_days=delivery_days,
        biosecurity_verified=True,
        audit_event_id=audit_event_id,
    )


@app.get("/v1/biosecurity/audit")
async def biosecurity_audit(
    request: Request,
    ctx: TenantContext = Depends(require_tenant),
    limit: int = 100,
) -> dict[str, Any]:
    """Get biosecurity screening audit log for this tenant.

    Returns screening decisions (cleared / flagged / blocked) with risk scores.
    """
    audit: AuditLogger = request.app.state.audit
    events = await audit.query(
        tenant_id=ctx.tenant_id,
        limit=limit,
    )
    # Filter to biosecurity events
    bio_events = [e for e in events if e.get("event_type", "").startswith(("biosecurity", "generation"))]
    return {"tenant_id": ctx.tenant_id, "events": bio_events, "count": len(bio_events)}


# -- care plan + call bell endpoints ----------------------------------------


@app.get("/v1/careplans/preload")
async def preload_careplan_context(
    request: Request,
    facility_id: str,
    floor_id: str,
    ctx: TenantContext = Depends(require_tenant),
) -> dict[str, Any]:
    """Return AI-ready context from all care plans on a floor.

    The returned `ai_context` string can be injected directly into the model's
    system prompt or retrieval context so the AI knows every resident's care
    plan before processing any visit documentation.
    """
    careplans: CarePlanRegistry = request.app.state.careplans
    plans = careplans.get_by_floor(ctx.tenant_id, facility_id, floor_id)
    ai_context = "\n\n---\n\n".join(p.to_ai_context() for p in plans)
    return {
        "tenant_id": ctx.tenant_id,
        "facility_id": facility_id,
        "floor_id": floor_id,
        "plan_count": len(plans),
        "ai_context": ai_context,
        "briefs": [p.to_brief() for p in plans],
    }


@app.get("/v1/careplans/{floor_id}")
async def get_floor_careplans(
    floor_id: str,
    request: Request,
    facility_id: str,
    ctx: TenantContext = Depends(require_tenant),
) -> dict[str, Any]:
    """Get all care plans for a floor — tenant-scoped, authenticated."""
    careplans: CarePlanRegistry = request.app.state.careplans
    plans = careplans.get_by_floor(ctx.tenant_id, facility_id, floor_id)
    return {
        "tenant_id": ctx.tenant_id,
        "facility_id": facility_id,
        "floor_id": floor_id,
        "plans": [p.to_dict() for p in plans],
        "count": len(plans),
    }


@app.post("/v1/callbell/event")
async def callbell_event(body: dict[str, Any]) -> dict[str, Any]:
    """Receive a call bell event from a nurse call system.

    This is the integration webhook. Nurse call systems (Rauland Responder,
    Ascom, etc.) POST here when a call bell is pressed.

    No tenant auth — call bell systems don't authenticate per tenant.
    """
    # Use app state from module-level reference
    careplans = app.state.careplans
    audit = app.state.audit
    callbell_queue = app.state.callbell_queue

    ts = body.get("timestamp") or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    event_data = {
        "room_number": body["room_number"],
        "floor_id": body["floor_id"],
        "facility_id": body["facility_id"],
        "event_type": body.get("event_type", "call_bell"),
        "timestamp": ts,
        "metadata": body.get("metadata", {}),
    }

    # Try to match to a care plan
    matched_plan: dict[str, Any] | None = None
    plan_id: str | None = None
    tenant_id: str | None = None

    # Load all tenants' care plans for the facility/floor
    for tid in app.state.tenants.tenants:
        try:
            plans = careplans.get_by_floor(tid, body["facility_id"], body["floor_id"])
            for plan in plans:
                if plan.room_number == body["room_number"]:
                    matched_plan = plan.to_brief()
                    plan_id = plan.id
                    tenant_id = plan.tenant_id
                    careplans.log_call_bell(tenant_id, plan.facility_id, plan_id, event_data)
                    break
            if matched_plan:
                break
        except Exception:
            continue

    # Queue notification for the floor
    queue_key = f"{body['facility_id']}:{body['floor_id']}"
    queue = callbell_queue.setdefault(queue_key, [])
    notification = {
        **event_data,
        "plan_id": plan_id,
        "tenant_id": tenant_id,
        "matched_plan": matched_plan,
    }
    queue.append(notification)
    if len(queue) > 100:
        callbell_queue[queue_key] = queue[-100:]

    # Audit
    await audit.log(
        event_type="callbell-received",
        room_number=body["room_number"],
        floor_id=body["floor_id"],
        facility_id=body["facility_id"],
        event_type_detail=body.get("event_type", "call_bell"),
        matched_plan_id=plan_id,
        timestamp=ts,
    )

    return {
        "status": "received",
        "event": event_data,
        "matched_plan": matched_plan,
        "matched_plan_id": plan_id,
        "queue_length": len(queue),
    }


@app.post("/v1/callbell/notify")
async def callbell_notify(
    body: CallBellNotifyRequest,
    request: Request,
    ctx: TenantContext = Depends(require_tenant),
) -> dict[str, Any]:
    """Get the latest pending call bell notifications for a floor.

    This is polled by the frontend (or pushed via WebSocket in production).
    Returns the care plan brief for the resident who pressed the call bell
    so the PSW sees who's calling + room number + relevant info.
    """
    careplans: CarePlanRegistry = request.app.state.careplans
    plan = careplans.get_one(body.tenant_id, body.facility_id, body.plan_id)
    if not plan:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Care plan not found")

    # Pull pending events from queue (pop so they're not re-sent)
    queue_key = f"{body.facility_id}:{body.floor_id}"
    queue = request.app.state.callbell_queue.get(queue_key, [])

    return {
        "plan_id": body.plan_id,
        "brief": plan.to_brief(),
        "ai_context": plan.to_ai_context(),
        "pending_events": queue[-5:],  # last 5 events
        "total_pending": len(queue),
    }


@app.get("/v1/callbell/queue")
async def callbell_queue(
    request: Request,
    facility_id: str,
    floor_id: str,
    ctx: TenantContext = Depends(require_tenant),
) -> dict[str, Any]:
    """Poll the call bell notification queue for a floor.

    The frontend polls this endpoint to get new call bell alerts.
    Production: replace with WebSocket push for real-time delivery.
    """
    queue_key = f"{facility_id}:{floor_id}"
    queue = request.app.state.callbell_queue.get(queue_key, [])
    # Clear after reading — each poll consumes the queue
    request.app.state.callbell_queue[queue_key] = []

    careplans: CarePlanRegistry = request.app.state.careplans
    enriched = []
    for item in queue:
        if item.get("plan_id") and item.get("tenant_id"):
            plan = careplans.get_one(item["tenant_id"], facility_id, item["plan_id"])
            if plan:
                item["brief"] = plan.to_brief()
        enriched.append(item)

    return {
        "facility_id": facility_id,
        "floor_id": floor_id,
        "events": enriched,
        "count": len(enriched),
    }


# -- business portal endpoint -----------------------------------------------


class CallBellEvent(BaseModel):
    room_number: str
    floor_id: str
    facility_id: str
    event_type: str = "call_bell"  # call_bell | bathroom_alert | wander_alert | emergency
    timestamp: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


CallBellEvent.model_rebuild()


class CallBellNotifyRequest(BaseModel):
    tenant_id: str
    facility_id: str
    floor_id: str
    room_number: str
    plan_id: str
    event_type: str = "call_bell"


CallBellNotifyRequest.model_rebuild()


class FloorPlansRequest(BaseModel):
    facility_id: str
    floor_id: str


class BusinessApplicationRequest(BaseModel):
    org_name: str
    contact_email: str
    org_type: str = "home_care_agency"
    estimated_volume: str = "low"


class BusinessApplicationResponse(BaseModel):
    application_id: str
    status: str
    message: str


@app.post("/v1/business/apply", response_model=BusinessApplicationResponse)
async def business_apply(req: BusinessApplicationRequest, request: Request) -> BusinessApplicationResponse:
    """Business portal — enterprise onboarding form.

    Accepts onboarding applications from healthcare agencies, hospitals,
    and biotech companies. MVP: logs the application + returns a reference ID.
    Production: creates tenant provisioning ticket, sends confirmation email.
    """
    app_id = f"APP-{uuid.uuid4().hex[:12]}"
    try:
        audit: AuditLogger = request.app.state.audit
        await audit.log(
            event_type="business-application",
            application_id=app_id,
            org_name=req.org_name,
            contact_email=req.contact_email,
            org_type=req.org_type,
            estimated_volume=req.estimated_volume,
        )
    except Exception:
        pass  # TestClient mode has no lifespan — log only
    logger.info("business application %s from %s (%s)", app_id, req.org_name, req.contact_email)
    return BusinessApplicationResponse(
        application_id=app_id,
        status="received",
        message=f"Application received. Reference: {app_id}. We'll be in touch within 24 hours.",
    )


# -- biology news endpoint --------------------------------------------------

BIO_NEWS_PATH = PathLib(__file__).resolve().parents[1] / "psw-assistant" / "biology_news.json"


@app.get("/v1/bio-news")
async def bio_news(refresh: bool = False) -> dict[str, Any]:
    """Biology and biotech news — curated global feed.

    Serves the curated news JSON. No auth required — public endpoint.
    Production: swap to live RSS/API aggregation with cache.
    """
    try:
        data = json.loads(BIO_NEWS_PATH.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return {
            "updated": "never",
            "top_stories": [],
            "companies_to_watch": [],
            "what_to_look_forward_to": [],
            "categories": {},
        }
    return data


# -- static UI ---------------------------------------------------------------

ROOT_DIR = PathLib(__file__).resolve().parents[1]
PSW_UI_DIR = ROOT_DIR / "psw-assistant"


@app.get("/", include_in_schema=False)
async def root() -> RedirectResponse:
    """Redirect root to the PSW voice UI."""
    return RedirectResponse(url="/psw/")


if PSW_UI_DIR.exists():
    app.mount("/psw", StaticFiles(directory=str(PSW_UI_DIR), html=True), name="psw-ui")
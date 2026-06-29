# Threat Model — openclinical-ai

Starting STRIDE-style analysis. Living document.

**Current version:** v0.2.0 (multi-tenant, home-care pivot)

## Assets

- **Patient health information (PHI)** flowing through inference pipeline
- **Model weights** in the registry (signing, provenance)
- **Audit logs** (tamper-resistance)
- **Consent records** (patient-controlled)
- **Inference results** (returned to calling systems)
- **Tenant isolation boundaries** (multi-tenant: agency-byok, audit, consent per tenant)
- **Tenant API keys + session tokens** (auth for per-tenant access)
- **Family-visible visit notes** (read-only, sanitized)
- **GPS visit verification data** (PHI under PHIPA)

## Trust boundaries

1. **External → API:** Clinical apps + family portal calling endpoints
2. **API → runtime:** Request validation, auth, consent check, sanitization
3. **Runtime → registry:** Model loading, Ed25519 signature verification
4. **Runtime → tenant registry:** Tenant lookup, encryption-model routing
5. **Runtime → audit gateway:** Tenant-scoped inference + visit events
6. **Runtime → consent engine:** Tenant-scoped consent check
7. **Runtime → response:** Sanitized results back to caller (no cross-tenant data)
8. **Tenant A ↔ Tenant B:** STRICT ISOLATION — no data flow, no shared process
9. **Audit gateway → external storage:** Long-term audit (FHIR server, S3) per tenant

## Threats (STRIDE)

### Spoofing

- **T-S1:** Forged model weight uploaded to registry
  - *Mitigation:* Ed25519-signed manifests (verified on load), SHA-256 hash pinning, registry mounted RO at runtime
- **T-S2:** Forged caller identity hitting inference API
  - *Mitigation:* Per-tenant API keys (SHA-256 hashed in storage), session tokens with 8h TTL, PSW ID in header
- **T-S3:** Forged session token (replay or stolen)
  - *Mitigation:* Session expiry, server-side session table, tenant_id + psw_id binding in session
- **T-S4:** Cross-tenant token reuse (Bayshore token used to hit Carefor)
  - *Mitigation:* Session record stores tenant_id; require_tenant() validates token's tenant_id matches X-Tenant-ID header

### Tampering

- **T-T1:** Audit log tampered after the fact
  - *Mitigation:* Append-only JSONL storage, hash chaining, periodic anchoring to immutable store
- **T-T2:** Model weights swapped at runtime
  - *Mitigation:* Ed25519 signature verification on load, registry mounted RO in container
- **T-T3:** Inference result tampered in transit
  - *Mitigation:* TLS, signed responses, response verification at caller
- **T-T4:** Tenant API key leaked
  - *Mitigation:* Keys stored hashed (SHA-256), plaintext shown once at creation, rotate via API; tenant can self-revoke

### Repudiation

- **T-R1:** Hospital denies a clinical decision was made by AI
  - *Mitigation:* Full audit trail with model version, input snapshot (sanitized), output, operator identity, tenant_id
- **T-R2:** PSW denies a visit was completed
  - *Mitigation:* GPS clock-in/clock-out events with lat/lng + timestamp, audit event IDs returned to UI

### Information disclosure

- **T-I1:** PHI leakage via prompt injection
  - *Mitigation:* Pre-inference sanitization (20+ injection patterns), structured prompting, output validation, audit-logged `prompt-injection-blocked` events
- **T-I2:** PHI leakage via inference timing attacks
  - *Mitigation:* Constant-time inference, batching, no per-tenant timing variance
- **T-I3:** Model inversion attack (recover training data from model)
  - *Mitigation:* Differential privacy during training, output perturbation, model adapter sandboxing
- **T-I4:** Registry enumeration
  - *Mitigation:* Authenticated registry access, audit on enumeration, public `/models` returns IDs + descriptions only
- **T-I5:** Cross-tenant data leakage (Tenant A's PSW sees Tenant B's visits)
  - *Mitigation:* `require_tenant()` dependency on every protected endpoint, visit queries filter by `tenant_id == ctx.tenant_id`, audit queries filter by `tenant_id`, per-tenant encryption keys (BYOK)
- **T-I6:** Family portal sees PHI instead of family-visible notes
  - *Mitigation:* Family portal uses separate token (not the PSW API key), endpoint returns only `family_visible_note` field with PHI sanitization
- **T-I7:** PSW free-text notes leak PHI into AI inference
  - *Mitigation:* `sanitize_free_text()` strips SSN/SIN/PHN patterns, max-length cap (32K chars), redacted substrings logged
- **T-I8:** Family-visible note accidentally contains clinical detail
  - *Mitigation:* Sanitization on store (separate from inference sanitization), structured input field, length cap (1K chars)
- **T-I9:** Tenant API key transmitted in cleartext
  - *Mitigation:* TLS required, CORS allowlist, server-side only over HTTPS in production

### Denial of service

- **T-D1:** Inference endpoint flooded
  - *Mitigation:* Rate limiting per tenant (planned), queue depth caps, circuit breakers per model
- **T-D2:** Expensive model triggered by low-priority caller
  - *Mitigation:* Tiered model access (planned), quota per tenant
- **T-D3:** Noisy-neighbor attack (Tenant A consumes resources, Tenant B suffers)
  - *Mitigation:* Per-tenant rate limits + resource quotas (planned), container-level isolation in production

### Elevation of privilege

- **T-E1:** Inference caller gets write access to audit log
  - *Mitigation:* Separate auth domains; audit gateway is write-only from caller perspective; audit query requires tenant_id (no "list all")
- **T-E2:** Compromised model gets network access at runtime
  - *Mitigation:* Sandboxed inference (gVisor, Firecracker), no network egress by default, model adapter pattern keeps model code isolated
- **T-E3:** Cross-tenant privilege escalation
  - *Mitigation:* `require_tenant()` rejects unknown tenant_ids, API key lookup validates hashed match, session token tenant binding
- **T-E4:** PSW gains tenant-admin privileges
  - *Mitigation:* PSW session tokens have no admin scope; tenant admin actions require separate auth (planned for v1)
- **T-E5:** Inference caller bypasses consent check
  - *Mitigation:* Consent check is non-optional in inference pipeline; missing/expired token → `consent-denied` event + HTTP 403

## Multi-tenant isolation model

**Architecture:** Hybrid silo + pool. Default = schema-per-tenant (per-tenant JSONL audit, per-tenant consent records). Silo mode available for high-security tenants (provincial health authorities, hospitals) with their own KMS key.

```
┌──────────────────────────────────────────────────────────────┐
│  openclinical-ai multi-tenant runtime                        │
├──────────────────────────────────────────────────────────────┤
│  Tenant A (Bayshore Ottawa)        Tenant B (Carefor Ottawa) │
│  ┌──────────────────────┐          ┌──────────────────────┐  │
│  │  Auth (OIDC + MFA)   │          │  Auth (OIDC + MFA)   │  │
│  │  BYOK: A's KMS key   │          │  BYOK: B's KMS key   │  │
│  │  Schema: bayshore_*  │          │  Schema: carefor_*   │  │
│  │  Audit: bayshore.log │          │  Audit: carefor.log  │  │
│  │  Consent: FHIR R4    │          │  Consent: FHIR R4    │  │
│  │  Model: signed       │          │  Model: signed       │  │
│  │  Rate: 100 req/s     │          │  Rate: 50 req/s      │  │
│  └──────────────────────┘          └──────────────────────┘  │
│       │                                    │                 │
│       └────────────┬───────────────────────┘                 │
│                    ▼                                         │
│  ┌──────────────────────────────────────────────────────┐    │
│  │  Shared infrastructure (hardened)                     │    │
│  │  - mTLS everywhere                                   │    │
│  │  - Zero-trust                                        │    │
│  │  - Per-tenant rate limits + quotas (planned)         │    │
│  │  - Per-tenant resource isolation                     │    │
│  └──────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────┘
```

**Defense-in-depth layers:**
1. Network — mTLS, zero-trust (planned)
2. Identity — per-tenant API keys (hashed), session tokens, PSW ID binding
3. Data — BYOK encryption, tenant-scoped queries
4. Compute — process-level isolation (planned: container-per-tenant silo mode)
5. Model — Ed25519 signed manifests, no network egress
6. Audit — per-tenant immutable log, FHIR AuditEvent export
7. Input — sanitization + prompt injection defense + structured prompting
8. Output — PHI redaction, family-visible sanitization, content classifiers (planned)

## Cross-cutting

- **Supply chain:** All dependencies pinned + signed (sigstore/cosign planned). Model weights Ed25519-signed + provenance verified.
- **AI-specific:** OWASP LLM Top 10 (2025) covered — prompt injection (T-I1), training data poisoning (T-I3), model DoS (T-D1, T-D2), supply chain (T-S1, T-T2). NIST AI RMF mapping in `docs/REGULATORY-MAPPING.md`.
- **Adversarial robustness:** Prompt-injection patterns catalogued in `runtime/sanitize.py`; injection attempts logged as `prompt-injection-blocked` audit events. Real clinical AI models must pass adversarial-robustness CI (planned).
- **Healthcare breach lessons (Change Healthcare 2024):**
  - One Citrix server without MFA → $2.9B+ impact
  - Lesson: MFA mandatory, network segmentation, immutable backups, kill switch
  - openclinical-ai: mandatory session expiry, tenant-scoped audit, append-only storage

## Compliance roadmap

| Framework | Status | Target |
|-----------|--------|--------|
| PHIPA technical safeguards (Ontario) | MVP aligned | Year 1 |
| Quebec Law 25 | MVP aligned | Year 1 |
| PIPEDA | MVP aligned | Year 1 |
| SOC 2 Type II | Planned | Year 1 |
| NIST CSF 2.0 | MVP aligned | Year 1 |
| ISO 27001 + 27018 | Planned | Year 1 |
| NIST AI RMF | Planned | Year 1 |
| HITRUST CSF | Planned | Year 2 |
| ISO/IEC 42001 (AI mgmt) | Planned | Year 2 |

## Out of scope (for now)

- Network-level attacks (DDoS at L3/L4) — handled by infra layer
- Physical security of hospital data centers — handled by hospital
- Insider threat from hospital staff with legitimate access — handled by hospital IAM
- Patient-side social engineering — handled by patient education
- Quantum-resistant cryptography — planned for v2 (when NIST PQC standards final)

## Bio-security threats (generative biology layer) — added 2026-06-28

### Biosecurity threat model

**Critical context:** [Science 2025 paper](https://www.science.org/doi/10.1126/science.adu8578) showed current DNA synthesis screening is inadequate against AI-redesigned protein sequences. openclinical-ai enforces multi-layer screening at the substrate level — not relying on downstream synthesis vendors.

### Biosecurity threats (STRIDE)

#### Spoofing (bio)
- **B-S1:** Forged generation request claiming to be from authorized tenant
  - *Mitigation:* Multi-tenant auth (`require_tenant()`), tenant_id in body must match X-Tenant-ID header, session token binding
- **B-S2:** Forged model output (model substitution attack — model returns different sequence than expected)
  - *Mitigation:* Ed25519-signed model manifests, SHA-256 hash pinning, reproducibility check, model version logged in every generation event

#### Tampering (bio)
- **B-T1:** Synthesis order tampered to ship different sequence than was screened
  - *Mitigation:* Biosecurity hash (SHA-256 of screened sequence) attached to order, vendor-side verification of hash before synthesis, audit trail
- **B-T2:** Generated sequence tampered in transit
  - *Mitigation:* TLS required, sequence_hash logged at generation time, vendor verifies hash

#### Repudiation (bio)
- **B-R1:** Researcher denies generating a flagged sequence
  - *Mitigation:* Full audit trail: tenant_id, psw_id, model_id + version, sequence_hash, biosecurity screening result, generation timestamp, audit_event_id, generation_id

#### Information disclosure (bio)
- **B-I1:** Generated sequence leaks via inference timing attack
  - *Mitigation:* Constant-time generation, batching, no per-tenant timing variance
- **B-I2:** Biosecurity screening logic disclosed via reverse-engineering
  - *Mitigation:* Screening patterns are public (IGS standard requires disclosure) but the screening decision audit log is tenant-encrypted (BYOK)
- **B-I3:** Cross-tenant generation data leakage (Tenant A generates sequence, Tenant B sees it)
  - *Mitigation:* Tenant-scoped audit, BYOK encryption on generation results, generation_id not predictable across tenants

#### Denial of service (bio)
- **B-D1:** Expensive generation flooded (Baker lab models need GPU)
  - *Mitigation:* Per-tenant rate limits, queue depth caps, GPU resource quotas per tenant
- **B-D2:** Synthesis vendor API flooded
  - *Mitigation:* Order queue, retry-with-backoff, vendor failover

#### Elevation of privilege (bio)
- **B-E1:** Researcher bypasses biosecurity screening
  - *Mitigation:* Screening is non-optional in the generation pipeline, sequence with risk_score > 0.7 raises HTTP 403, blocked events logged as `biosecurity-blocked`
- **B-E2:** Synthesis vendor order accepted without biosecurity screening
  - *Mitigation:* `/v1/synthesis/order` requires biosecurity_hash matching a recent `generation-cleared` audit event, hash verified before submission
- **B-E3:** AI-evasion sequence evades pathogen similarity screening
  - *Mitigation:* Multi-layer screening (pathogen signatures + toxin motifs + evasion patterns + length sanity + composition), IGS-compliant screening standard, future: ML-based evasion detection

### Bio-security defense layers

1. **Generation layer** — every model adapter returns to base class, base class calls screener before returning
2. **HTTP layer** — `/v1/generate/*` endpoints require `require_tenant()`, screened result in response
3. **Audit layer** — every screening decision logged with risk_score + flags
4. **Synthesis layer** — `/v1/synthesis/order` requires biosecurity_hash matching a cleared generation event
5. **Vendor layer** — openclinical-ai's biosecurity screening result attached to vendor order so vendor sees what we caught

### Biosecurity screening layers (5)

1. **Pathogen signatures** — curated patterns for botulinum, anthrax, ricin, SARS-CoV-2, Ebola, influenza, smallpox, select agents
2. **Toxin / virulence motifs** — disulfide loops, catalytic triads, metalloproteases, T3SS motifs
3. **AI-evasion patterns** — polybasic stretches, low-complexity glycine-rich regions, unknown residue runs
4. **Length sanity** — sequences too short or too long flagged
5. **Composition** — invalid amino acid / base rates > 5% flagged

Production upgrades (planned):
- Real BLAST alignment against NCBI pathogen databases
- HHS/USDA select agent list enforcement
- ML-based evasion detection
- IGS International Gene Synthesis Consortium screening (full compliance)

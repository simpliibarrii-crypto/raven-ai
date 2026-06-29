# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| main    | :white_check_mark: |
| < older | :x:                |

## Reporting a Vulnerability

We take security seriously, especially given the healthcare context. If you discover a vulnerability:

1. **DO NOT** open a public issue.
2. Email security@openclinical-ai.example with details.
3. We will acknowledge within 48 hours and provide a remediation timeline.

For critical vulnerabilities (PHI exposure, model tampering, audit log bypass, cross-tenant data leakage), we aim to ship a fix within 7 days.

## Multi-tenant security posture

openclinical-ai is designed so any healthcare service can connect to it but each tenant is isolated from every other tenant. Security boundaries:

**Authentication:**
- Per-tenant API keys (SHA-256 hashed in storage, plaintext shown once at creation)
- Per-PSW session tokens (8-hour TTL, server-side session table)
- Tenant ID + PSW ID validated on every protected request
- Cross-tenant token reuse rejected with HTTP 401

**Authorization:**
- `require_tenant()` FastAPI dependency on every protected endpoint
- Visit + audit + consent queries filtered by `tenant_id == ctx.tenant_id`
- Family portal uses separate token (not PSW API key)

**Encryption:**
- Three encryption models: agency-BYOK (recommended), platform-managed, shared (demo only)
- BYOK: tenant brings their own KMS key (AWS KMS, Azure Key Vault, GCP KMS, HashiCorp Vault)
- Audit + consent + visit data encrypted with tenant-held key
- openclinical-ai cannot decrypt without tenant permission in BYOK modebolita**Audit:**
- Per-tenant append-only JSONL audit log
- FHIR AuditEvent-compatible format
- No "list all tenants" query — every query requires `tenant_id`
- Cross-tenant query attempts logged as `cross-tenant-access-blocked` audit events

**Input defense:**
- All free-text PSW notes sanitized for prompt-injection before AI inference
- 20+ injection patterns detected + redacted (see `runtime/sanitize.py`)
- Structured observation fields have HTML/script characters stripped
- Sanitization events logged as `prompt-injection-blocked` audit eventsboleta**Output defense:**
- Inference outputs returned to caller only after sanitization
- Family portal returns only `family_visible_note` field (separate sanitization)
- PHI patterns (SSN/SIN/PHN) redacted at multiple layers

## Scope

In scope:
- Inference runtime vulnerabilities (sandbox escape, model poisoning)
- Audit gateway tampering or bypass
- Consent engine bypass
- Registry signature verification bypass
- FHIR auth/authz bypass
- PHI leakage via inference
- **Cross-tenant data leakage** (multi-tenant isolation bypass)
- **Prompt injection** (OWASP LLM01:2025)
- **Tenant API key compromise** (storage, rotation, revocation)
- **Session token theft/replay** (expiry, binding)
- **GPS data exposure** (visit verification PHI)
- **Family portal PHI leakage** (cross-field contamination)

Out of scope:
- Issues in upstream dependencies (report to them)
- Hospital infrastructure-level attacks (report to hospital IT)
- Social engineering
- Patient-side device compromise

## Threat model

See `docs/THREAT-MODEL.md` for the full STRIDE-style threat model and multi-tenant isolation architecture.

## Compliance

| Framework | Status |
|-----------|--------|
| PHIPA technical safeguards (Ontario) | MVP aligned |
| Quebec Law 25 | MVP aligned |
| PIPEDA | MVP aligned |
| NIST CSF 2.0 | MVP aligned |
| SOC 2 Type II | Planned Year 1 |
| ISO 27001 + 27018 | Planned Year 1 |
| HITRUST CSF | Planned Year 2 |
| ISO/IEC 42001 (AI mgmt) | Planned Year 2 |
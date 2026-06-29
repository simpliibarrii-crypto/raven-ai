# openclinical-ai

**The hub of AI for healthcare and biology — open sovereign deployment substrate for biology AI and clinical AI. Multi-tenant by design. Any healthcare service can connect, each tenant stays isolated. Affordable for everyone.**

Apache 2.0 · [github.com/simpliibarrii-crypto/openclinical-ai](https://github.com/simpliibarrii-crypto/openclinical-ai)
**Runs on macOS, Windows, Linux (Ubuntu/Debian, Fedora/RHEL, Arch, Alpine), iOS, Android — browser + Python 3.11+ anywhere.**

---

## What this is

An open-source runtime for deploying clinical AI models (and biology AI models) with:

- **Sovereign inference** — runs in the same jurisdiction as patient data. No cloud round-trips.
- **Multi-tenant by design** — any healthcare service can connect, each tenant isolated with its own encryption keys, audit log, consent records, and rate limits.
- **Bring Your Own Key (BYOK)** — tenants bring their own KMS key (AWS KMS, Azure Key Vault, GCP KMS, HashiCorp Vault). openclinical-ai cannot decrypt PHI without tenant permission.
- **Signed model registry** — every model artifact is Ed25519-signed; unsigned models rejected by default.
- **Audit gateway** — every inference logged in FHIR AuditEvent-compatible format, tenant-scoped.
- **Consent engine** — PHIPA-aligned opt-in consent, propagated to every call.
- **Prompt-injection defense** — PSW free-text notes sanitized for 20+ injection patterns before AI inference. OWASP LLM01:2025 covered.
- **Voice-first home care UI** — visit documentation demo at `/psw/`. GPS check-in, family-visible notes, multi-visit/day, billing-ready timestamps.
- **Family portal** — read-only view of family-visible visit notes. No PHI. Separate token from PSW API key.
- **Affordability tiers** — DeepSeek V4-Pro / V4-Flash pricing model, equity-first resource policy. Cost transparency per tenant. See "Affordability" below.
- **Single-container deploy** — Docker, docker-compose, K8s-ready.

---

## Affordability — affordable for everyone (v0.3.0)

The substrate is designed so the same clinical-quality inference is reachable by a rural critical-access hospital, a 200-bed LTC home, a regional hospital, and an academic medical center — without the substrate penalizing smaller institutions.

Seven tiers, mapped onto Canadian healthcare institution types:

| Tier | Default model | Default quantization | Max context | Example institutions |
|------|---------------|---------------------|-------------|----------------------|
| `critical_access_rural` | V4-Flash / DSpark | fp8 | 32K | WAHA, remote nursing stations |
| `ltc_home` | V4-Flash | fp8 | 32K | Garry J Armstrong, Perley Health, Revera |
| `home_care_agency` | V4-Flash | fp8 | 16K | Bayshore, Carefor, VHA, SE Health, ParaMed |
| `regional_hospital` | V4-Pro | fp16 | 128K | The Ottawa Hospital, CHEO, regional authorities |
| `academic_medical_center` | V4-Pro | fp16 | 1M | UHN, Sunnybrook, Mount Sinai, VGH |
| `biotech_research` | V4-Pro | fp16 | 1M | Mila, Vector, NRC, AbCellera |
| `biotech_sovereign` | DSpark on-prem | fp16 | hardware-bounded | Air-gapped sovereign deployments |

**Pricing model** (anchored in published DeepSeek rates as of 2026-05-22):
- **V4-Pro**: $0.435/M input + $0.87/M output tokens
- **V4-Flash**: $0.10/M input + $0.30/M output tokens (estimate)
- **DSpark on-prem**: $0 marginal API cost after initial setup
- **Closed-source baselines** (for savings reporting): GPT-5.5 ~$10/$30, Opus 4.7 ~$15/$75

**Per-tenant cost transparency**: every inference is cost-tracked and reported back to the requesting tenant via `/v1/cost/report`. Reports are tenant-scoped — no cross-tenant visibility. Affordability is for the patient, not for tenant-vs-tenant comparison.

**Equity-first invariant**: every tier has full feature parity. Smaller institutions get tighter resource ceilings (max context, rate limits) — never denied capabilities. Clinical-decision-class models (drug interaction, variant impact, adverse event detection, fall risk) always default to fp16 regardless of tier — regulator-facing determinism isn't a tier policy.

**Reference architectures mirrored:**
- **DeepSeek V4-Pro** — 1.6T params, 49B activated (3% sparsity), hybrid CSA+HCA attention, 27% FLOPs + 10% KV cache vs V3.2
- **DeepSeek V4-Pro-DSpark** — MIT-licensed on-prem inference framework paired with the open DeepSpec training repo
- See `runtime/efficient.py` for the substrate-side seams these patterns slot into

### New in v0.4.0

- **Security hardening**: `/audit/events` now requires tenant authentication (was public). Family portal token moved from query param to `X-Family-Token` header. Default consent scope narrowed from `["*"]` to `["visit_documentation"]`. Demo visits gated behind `OPENCLINICAL_ENV != production`.
- **White + red theme** — clinical crimson `#C8102E` (not Red Cross red). Light/dark mode toggle persisted to `localStorage`.
- **Distinctive logo** — interlocking OC rings SVG in `psw-assistant/assets/logo.svg`. No crosses, no humanitarian symbols.
- **French + English i18n** — `locales/en.json` + `locales/fr.json` (126 keys each). Language switcher in Settings, persisted to `localStorage`. Voice dictation language matches active locale. Spanish, Chinese, Arabic buttons in Settings (locales to follow).
- **Connectors tab** — 18 healthcare/biotech systems listed with honest status badges: `available` / `in-development` / `planned` / `community`. FHIR R4 and synthesis vendors (Twist, IDT, GenScript) are `available` today.
- **Business portal** — `/v1/business/apply` endpoint + in-app form. Enterprise onboarding in 3 steps for hospitals, home care agencies, LTC homes, and biotech companies.
- **Minimal button UX** — bottom tab bar (Visits · Connect · Settings) replaces button clusters. One primary action per screen. Voice dictation is the default input path.
- **Cross-platform** — PWA manifest for installable web app on iOS, Android, and desktop. Docker + Linux native. Runs anywhere with a browser and Python 3.11+.
- **0 external frontend dependencies** — the entire UI is a single HTML file + CSS + JS. No npm, no bundler, no CDN.

### New in v0.3.0

- `runtime/affordability.py` — tier definitions, per-model quantization policy, FLOPs + cost estimators
- `runtime/cost.py` — per-tenant cost tracker (tenant-scoped reports only)
- `runtime/efficient.py` — MoE expert router + hybrid attention compressor (interface only)
- `GET /v1/affordability/tiers` — public list of all tiers
- `GET /v1/affordability/eligibility` — what the current tenant qualifies for
- `POST /v1/inference/tier` — preview cost before committing to an inference
- `GET /v1/cost/report` — per-tenant cost report (since optional)

## Multi-tenant architecture

```
┌─────────────────────────────────────────────────────────────┐
│  openclinical-ai runtime  (multi-tenant, sovereign)          │
├─────────────────────────────────────────────────────────────┤
│  Tenant A (Bayshore Ottawa)         Tenant B (Carefor Ottawa)│
│  ┌──────────────────────┐           ┌──────────────────────┐  │
│  │  Auth: per-tenant    │           │  Auth: per-tenant    │  │
│  │  BYOK: A's KMS key   │           │  BYOK: B's KMS key   │  │
│  │  Audit: per-tenant   │           │  Audit: per-tenant   │  │
│  │  Consent: per-tenant │           │  Consent: per-tenant │  │
│  │  Rate: per-tenant    │           │  Rate: per-tenant    │  │
│  └──────────────────────┘           └──────────────────────┘  │
│       │                                    │                 │
│       └────────────┬───────────────────────┘                 │
│                    ▼                                         │
│  ┌──────────────────────────────────────────────────────┐    │
│  │  Shared hardened infrastructure                       │    │
│  │  - Signed model registry (Ed25519)                    │    │
│  │  - Audit gateway (FHIR AuditEvent-compatible)         │    │
│  │  - Consent engine (PHIPA-aligned)                     │    │
│  │  - Input sanitization (20+ injection patterns)        │    │
│  │  - mTLS + zero-trust (production)                     │    │
│  └──────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

**Defense-in-depth:** mTLS, zero-trust, per-tenant API keys (SHA-256 hashed), session tokens (8h TTL), Ed25519 model signatures, append-only audit logs, prompt-injection sanitization, BYOK encryption.

## Quickstart

### Run locally (60 seconds)

```bash
git clone https://github.com/simpliabarrii-crypto/openclinical-ai.git
cd openclinical-ai
python3 -m pip install 'fastapi>=0.110' 'uvicorn[standard]>=0.27' 'pydantic>=2.6' 'pynacl>=1.5' 'httpx>=0.27'

# Generate the demo signing key + signed model manifest
python3 tools/sign_manifest.py

# Start the runtime + voice UI
./run_dev.sh
```

Open http://localhost:8088 — the runtime redirects to the voice-first home care visit assistant.

### Run with Docker

```bash
docker-compose up --build
```

Then open http://localhost:8088.

### Try the demo end-to-end

1. Open http://localhost:8088 — pick your agency from the dropdown (Bayshore Ottawa, Carefor Ottawa, VHA Toronto)
2. Sign in as `psw-brian` (any PSW ID works for the demo)
3. See today's visits for that tenant (each tenant has its own visit list)
4. Click a visit → fill vitals + dictate notes → click **Generate visit summary**
5. See the structured summary + audit ID + sanitization report
6. Click **Family portal** to see what family caregivers see (read-only, sanitized)

### Smoke test the multi-tenant runtime

```bash
bash tools/smoke_test.sh
```

Verifies:
- `/health` returns version 0.3.0
- `/v1/tenants` returns 5 demo tenants (across all affordability tiers)
- Sign-in works for all 5 tenants
- Tenant A cannot see Tenant B's visits or cost reports (isolation verified)
- Prompt-injection attempts are redacted + logged as `prompt-injection-blocked`
- GPS visit clock-in works with audit trail
- Cost tracking per inference + per-tenant report works
- Affordability tier eligibility + cost preview works

## What's in the box (MVP v0.3.0)

| Component | Path | Status |
|-----------|------|--------|
| **Inference runtime** | `runtime/server.py` | ✅ working |
| **Multi-tenant registry** | `runtime/tenants.py` | ✅ 5 demo tenants (all tiers) |
| **Signed model registry** | `registry/`, `runtime/models.py` | ✅ Ed25519 verified |
| **Audit gateway** | `runtime/audit.py` | ✅ tenant-scoped |
| **Consent engine** | `runtime/consent.py` | ✅ PHIPA-aligned |
| **Input sanitization** | `runtime/sanitize.py` | ✅ 20+ injection patterns |
| **Voice-first UI** | `psw-assistant/` | ✅ home care visit docs |
| **Family portal** | `psw-assistant/` (family route) | ✅ read-only |
| **Visit lifecycle** | `runtime/server.py:/v1/visits/*` | ✅ clock-in/out + GPS |
| **PSW shift-handoff adapter** | `runtime/models.py:PSWShiftHandoffAdapter` | ✅ heuristic MVP |
| **Affordability tiers** | `runtime/affordability.py` | ✅ 7 tiers, equity-first |
| **Cost transparency** | `runtime/cost.py` | ✅ tenant-scoped reports |
| **Efficient inference seams** | `runtime/efficient.py` | ✅ MoE router + CSA/HCA compressor (interface) |
| **Generative biology + biosecurity** | `biology_ai/`, `runtime/bio_security.py` | ✅ 5-layer screening |
| **Smoke test** | `tools/smoke_test.sh` | ✅ all endpoints |
| **Tests** | `tests/test_substrate.py`, `test_affordability.py`, `test_efficient.py` | ✅ 57/57 pass |
| **Dockerfile** | `Dockerfile` | ✅ single container |
| **docker-compose** | `docker-compose.yml` | ✅ persistence |
| **Threat model** | `docs/THREAT-MODEL.md` | ✅ STRIDE + multi-tenant |
| **Security policy** | `SECURITY.md` | ✅ multi-tenant scope |
| Model card schema | `registry/MODEL-CARD.md` | ⏳ draft |
| FHIR Consent integration | `fhir/` | ⏳ scaffolded |
| DSpark integration | (planned) | ⏳ interface defined, server not integrated |
| Real MoE expert routing | (planned) | ⏳ seams in place, real routing is v2 |
| FP8 quantized runtime | (planned) | ⏳ policy hook is v1, runtime is v2 |
| K8s manifests | `deploy/` | ⏳ scaffolded |
| Compliance pack | `compliance/` | ⏳ scaffolded |

## API endpoints

| Endpoint | Auth | Purpose |
|----------|------|---------|
| `GET /health` | none | Runtime health + tenant count |
| `GET /models` | none | List loaded models (no secrets) |
| `GET /v1/tenants` | none | List tenants (no secrets) |
| `POST /v1/auth/signin` | none | Sign in PSW into tenant, get session token |
| `POST /v1/consent/grant` | tenant | Grant consent |
| `POST /v1/consent/revoke` | tenant | Revoke consent |
| `POST /v1/inference` | tenant | Run inference (sanitized, audited, cost-tracked) |
| `GET /v1/visits/today` | tenant | PSW's visits for today |
| `GET /v1/visits/:id` | tenant | Visit details |
| `POST /v1/visits/clock-in` | tenant | GPS clock-in for visit |
| `POST /v1/visits/clock-out` | tenant | Finalize visit |
| `GET /v1/family/timeline` | family token | Family portal (read-only) |
| `GET /v1/affordability/tiers` | none | List all affordability tiers |
| `GET /v1/affordability/eligibility` | tenant | What the current tenant qualifies for |
| `POST /v1/inference/tier` | tenant | Preview tier + cost for a request |
| `GET /v1/cost/report` | tenant | Per-tenant cost report (tenant-scoped ONLY) |
| `POST /v1/generate/{protein,binder,rna,dna}` | tenant | Generative biology (biosecurity-gated) |
| `POST /v1/synthesis/order` | tenant | Submit to Twist/IDT/GenScript |
| `GET /v1/biosecurity/audit` | tenant | Biosecurity screening audit log |
| `GET /audit/events` | tenant | Tenant-scoped audit log |
| `GET /psw/` | none | PSW UI |

## What the home care wedge solves

Canadian home care agencies struggle with:
- **PSW documentation burden** — 30-45 min/visit of paperwork eats into care hours
- **Illegible handwriting** — paper records fail audit + care continuity
- **No real-time family visibility** — family caregivers rely on phone calls
- **No voice input** — every existing tool requires typed notes
- **GPS visit verification gaps** — billing disputes, missed visits
- **Multi-agency coordination** — clients often use 2-3 agencies; no shared record
- **PHIPA audit trail gaps** — most tools log "who accessed" but not "what was decided" by AI
- **Vendor lock-in** — proprietary data formats, can't extract your own clinical record

openclinical-ai:
- Voice-first PSW UI → less typing, faster documentation
- GPS visit verification → billing-audit-ready timestamps
- Family portal → real-time visibility without PHI leak
- Multi-tenant → each agency isolated, no cross-agency data flow
- Prompt-injection sanitization → PSW free-text can't extract other tenants' PHI
- FHIR-native → integrates with existing EHRs (planned)
- Apache 2.0 → no vendor lock-in

## What's coming

The MVP demonstrates the multi-tenant substrate architecture. The roadmap is to plug in real models + production hardening:

1. **Real PSW AI** — replace heuristic with fine-tuned clinical LLM trained on anonymized PSW visit notes
2. **Biology AI** — protein-folding adapter, variant-effect predictor, on Canadian sovereign compute (TamIA / Nibi / Trillium)
3. **Hospital integration** — FHIR R4 server adapter, SMART-on-FHIR auth, CDS Hooks
4. **Adversarial-robustness CI** — automated red-teaming of models before they're signed into the registry
5. **Edge tier** — Jetson Orin / Coral / Hailo deployment for retirement homes and remote clinics
6. **Compliance** — SOC 2 Type II (Year 1), ISO 27001 + 27018 (Year 1), HITRUST (Year 2), ISO/IEC 42001 (Year 2)

## Why this matters

AlphaFold (UK), RoseTTAFold (US), ESM-3 (Meta US) — the foundational biology AI models are all foreign. Canadian biotech (AbCellera, Deep Genomics) is closed-source.

Clinical AI in Canadian hospitals runs on US vendor stacks (Epic Cosmos, Microsoft DAX, Nuance). PHIPA compliance is bolted on after the fact.

Home care documentation runs on paper, Excel, or proprietary SaaS (AlayaCare, PointClickCare, CellTrak) — none of which is sovereign, voice-first, or family-portal-equipped.

openclinical-ai is the open substrate everyone builds on:
- **Home care agencies** deploy sovereign visit documentation without vendor lock-in
- **Hospitals** deploy sovereign clinical AI with PHIPA + Quebec Law 25 alignment
- **Researchers** publish models with signed provenance + audit trail
- **Patients** consent is propagated to every call, not just recorded
- **Citizens** Canadian genomic + clinical data stays in Canada

## License

Apache 2.0. See [LICENSE](LICENSE).

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). All contributions require a CLA (signing over assignment of copyright to the project, with explicit license-back to Apache 2.0). This protects both contributors and downstream users.

---

**Built in Ottawa, for Canada, by a Personal Support Worker who knows what frontline care actually looks like.**
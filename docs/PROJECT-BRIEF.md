# Project Brief — openclinical-ai

## Mission

Provide the open, sovereign, Canadian-built deployment substrate for biology AI and clinical AI, so any Canadian — PSW, nurse, doctor, researcher, patient — can access foundational biological intelligence (protein folding, variant impact, drug-target identification, drug-interaction prediction) as public infrastructure, regardless of institution, geography, or budget.

Inspired by AlphaFold's model: open foundational AI as a public good, deployed freely, accessible to everyone. Applied to Canada's universal healthcare system.

## The root problem

Across six parallel research streams (vendor landscape, cybersecurity, system unification, regulatory, open-source foundations, hardware/edge inference) plus the Canadian biology AI landscape, the same gap surfaces under different names:

- **Canadian biology AI sovereignty:** AlphaFold (UK), RoseTTAFold (US), ESM-3 (Meta, US). All major biology foundation models are foreign. Canada's biotech AI (AbCellera, Deep Genomics) is closed-source, not shared. Canadian hospitals feed data to US AI vendors (Epic, Oracle Health). There is no open Canadian biology AI.
- **Cybersecurity brief:** "Clinical AI inference gateway + signed model registry + adversarial-robustness CI" is a greenfield infrastructure category — no incumbent owns it.
- **Open-source foundations:** "Missing layer is a cohesive, permissive, production-grade agentic + privacy + deployment stack." Four gaps identified:
  - (a) OSS clinical-AI agent runtime with audit and consent
  - (b) canonical hospital-on-K8s reference
  - (c) OSS confidential-computing primitives for clinical ML
  - (d) permissive-weight medical-imaging foundation models
- **Unification:** Epic holds ~70% of new hospital contracts; Cosmos has 300M+ records. 60% of US beds on non-Epic EHRs underserved. Vendor-neutral FHIR data fabric is the gap.
- **Vendor landscape:** 41% of hospitals cite lack of model cards + drift documentation as their top AI audit barrier (Becker's Nov 2025 CIO survey). HHS AI inventory deadline was Apr 2026 — now overdue.
- **Regulatory:** EU AI Act high-risk conformity assessments due Aug 2026 / Aug 2027. FDA PCCP standard now. HIPAA Security Rule update for AI training data. Health Canada medical device regulations.
- **Hardware:** Edge inference (Clara/Holoscan, OpenVINO, Hailo) + confidential compute (SGX, SEV, H100 CC) exists as components but no integrated open substrate ties them together.

## What we're building

An open-source monorepo providing the deployment substrate every biology AI and clinical AI app depends on:

| Component | Purpose |
|---|---|
| `runtime/` | Inference runtime (CPU/GPU/edge), multi-model — biology models + clinical models |
| `registry/` | Signed model registry, provenance, model cards, drift monitoring |
| `audit-gateway/` | Every inference logged, consent-aware, FHIR AuditEvent export |
| `consent/` | Patient consent propagated across the inference pipeline |
| `compliance/` | HIPAA / PHIPA / EU AI Act / Health Canada alignment artifacts |
| `deploy/` | Kubernetes (cloud/on-prem), single-node (edge), Compose (dev) |
| `fhir/` | FHIR-native identity, SMART-on-FHIR auth, CDS Hooks |
| `psw-assistant/` | **PSW-first vertical** — shift handoff, ADL tracking, fall risk, family comms |
| `biology-ai/` | **Biology AI vertical** — protein folding, variant impact, drug-target ID, drug interaction |
| `docs/` | Project brief, threat model, regulator mapping, Canadian strategy |

## Tracks (parallel)

**Track A — Clinical AI substrate (immediate build):**
- Runtime, registry, audit gateway, consent, compliance, deploy, FHIR-native identity
- PSW assistant as the first user-facing vertical
- Pilot at Gary J Armstrong Retirement Home (Ottawa)
- Ottawa retirement homes + Ontario LTC regulatory alignment

**Track B — Biology AI for Canadian clinical use (new focus):**
- Apply AlphaFold's model (open foundational AI + public database + accessible deployment) to Canadian clinical problems
- Identify Canadian biology AI models we could deploy (Mila's protein generation, UHN's clinical AI, etc.)
- Map substrate requirements for hosting AlphaFold-class models (GPU tier, inference throughput, edge deployment)
- Partner with Canadian biology AI labs (Mila, Vector, UHN, Deep Genomics, AbCellera, NRC, OHRI)
- Long-term: variant-impact predictor for Canadian rare disease diagnosis, drug-interaction predictor for PSWs, drug-target identification for Canadian-relevant conditions

**Track C — Canadian sovereignty (advocacy track, parallel):**
- Document the gap (Canadian health data flowing to US/UK AI vendors; no open Canadian biology AI)
- Build coalition (researchers, hospitals, patients, advocates)
- Propose the alternative: open biology AI for Canadian healthcare, hosted on Canadian infrastructure
- Push for funding (Genome Canada, NRC, CIHR, provincial health ministries, Pan-Canadian AI Strategy)

## Why now

- **AlphaFold's 2024 Nobel Prize** validated the open-foundational-AI-for-science model. Canada needs its own equivalent.
- **EU AI Act** high-risk conformity assessments hit in **Aug 2026 / Aug 2027** — forcing function for compliance-by-default designs.
- **HHS AI inventory deadline** (Apr 2026) is now overdue — hospitals are scrambling for AI transparency tooling.
- **Epic dominance + 60% non-Epic underserved** creates structural gap for vendor-neutral alternatives.
- **No open Canadian biology AI exists** — greenfield opportunity for sovereignty.
- **Pan-Canadian AI Strategy** ($443M committed 2024-2025, additional funding expected) provides funding path.

## Target users

- **PSWs in retirement homes, long-term care, home care** — voice-first AI for shift handoff, ADL tracking, fall risk
- **Nurses, doctors, allied health** — clinical decision support, drug interaction prediction, variant impact
- **Clinical AI vendors** — build on the substrate, get compliance for free
- **Researchers** — deploy biology models (protein folding, variant impact) to clinical environments
- **Critical-access and rural hospitals** — run on edge hardware with the same compliance posture
- **Canadian patients and families** — access biology AI (variant impact, drug interaction) as public infrastructure

## Built on

- **Biology AI references:** AlphaFold (DB + code + weights), RoseTTAFold, ESM-3, Mila protein generation models
- **Clinical AI efficiency:** DeepSeek V4-Pro (1.6T params / 49B activated MoE, hybrid CSA+HCA attention, MIT-licensed, $0.435/$0.87 per 1M tokens), DeepSeek V4-Flash (284B / 13B activated, MIT-licensed), DeepSeek V4-Pro-DSpark (MIT-licensed open-source inference framework, paired with DeepSpec training repo — designed for fully auditable on-prem deployment)
- **FHIR servers:** HAPI FHIR (2.4k★), Medplum (2.5k★)
- **Imaging AI:** MONAI (8.4k★), nnU-Net (8.6k★)
- **Federated learning:** NVIDIA FLARE, Flower (6.7k★)
- **Research data:** OHDSI/OMOP
- **Edge inference:** NVIDIA Clara/Holoscan, Intel OpenVINO, Hailo
- **Confidential compute:** Intel SGX, AMD SEV, NVIDIA H100/H200 CC
- **Canadian biology AI:** Mila, Vector, Deep Genomics, AbCellera, NRC, OHRI

## Affordability policy (v0.3.0 — added 2026-06-28)

The "affordable for everyone" mandate is operationalized through an affordability tier system that anchors in DeepSeek V4-Pro / V4-Flash's published pricing. The principle: every tier has **full feature parity** — only resource ceilings change (max context, rate limits), never denied capabilities.

| Tier | Default model | Quantization | Max context | Example institutions |
|------|---------------|--------------|-------------|----------------------|
| `critical_access_rural` | V4-Flash / DSpark | fp8 | 32K | WAHA, remote nursing stations |
| `ltc_home` | V4-Flash | fp8 | 32K | Garry J Armstrong, Perley Health, Revera |
| `home_care_agency` | V4-Flash | fp8 | 16K | Bayshore, Carefor, VHA, SE Health, ParaMed |
| `regional_hospital` | V4-Pro | fp16 | 128K | The Ottawa Hospital, CHEO |
| `academic_medical_center` | V4-Pro | fp16 | 1M | UHN, Sunnybrook, Mount Sinai, VGH |
| `biotech_research` | V4-Pro | fp16 | 1M | Mila, Vector, NRC, AbCellera |
| `biotech_sovereign` | DSpark on-prem | fp16 | hardware-bounded | Air-gapped sovereign deployments |

**Cost economics** (published V4-Pro pricing as of 2026-05-22):
- V4-Pro: $0.435/M input + $0.87/M output tokens
- V4-Flash: $0.10/M input + $0.30/M output tokens (estimate)
- DSpark on-prem: $0 marginal API cost after initial setup
- Closed-source baseline (for savings reporting): GPT-5.5 ~$10/$30, Opus 4.7 ~$15/$75

**Reference home-care economics (Bayshore Ottawa, 100 inferences/day, 1000 in / 500 out tokens):**
- Estimated monthly cost: $0.75 (V4-Flash pricing)
- Same volume on GPT-5.5: $75.00 (100x more expensive)
- Same volume on Opus 4.7: $157.50 (210x more expensive)

**Equity-first invariants:**
1. Every tier has full feature parity — no tier is denied a capability.
2. Quantization defaults are per-model, not per-tenant. Clinical-decision-class models (drug interaction, variant impact, adverse event detection, fall risk) always default to fp16 regardless of tier — regulator-facing determinism isn't a tier policy.
3. Per-tenant cost reports are tenant-scoped ONLY — no cross-tenant visibility. Affordability is for the patient, not for tenant-vs-tenant competitive comparison.
4. biotech_sovereign uses DSpark on-prem at $0 marginal API cost — sovereignty is the policy, not an optimization.

**DSpark as deployment target (planned v2):** DeepSeek V4-Pro-DSpark is the MIT-licensed open-source inference framework paired with the open DeepSpec training repo. DSpark is designed for fully auditable, air-gapped on-prem deployment — exactly the deployment story openclinical-ai's sovereign-tier (biotech_sovereign) is built for. v0.3.0 ships the substrate-side seams (`runtime/efficient.py` interface, `runtime/affordability.py` policy, `runtime/cost.py` accounting); v2 integrates an actual DSpark server adapter.

## Roadmap (initial 12 months)

- **Q3 2026:** Runtime + registry MVP. Basic inference + signed model loading + audit log. Pilot PSW assistant at Gary J Armstrong.
- **Q4 2026:** FHIR integration. SMART-on-FHIR auth + consent engine + audit gateway. Variant-impact predictor MVP using AlphaFold-class model.
- **Q1 2027:** Compliance pack. HIPAA / PHIPA / EU AI Act / Health Canada alignment artifacts. PSW assistant expanded to Ottawa retirement homes.
- **Q2 2027:** Edge tier. Single-node deployment for resource-limited settings. Confidential compute integration. Biology AI partner integrations (Mila, Vector).

## Canadian partners (research, not yet contacted)

- **Mila** (Montreal) — protein design, generative biology. Open-source protein generation models.
- **Vector Institute** (Toronto) — health AI, partnership with UHN.
- **Deep Genomics** (Toronto) — AI for rare disease drug discovery.
- **AbCellera** (Vancouver) — antibody discovery AI.
- **NRC** — biotech AI programs, IRAP funding.
- **Genome Canada / CGEn** — genomic medicine infrastructure.
- **Alliance Canada** — academic compute, GPU access.
- **UHN** (Toronto) — major AI-in-medicine program (SPARC, radiology AI, drug discovery).
- **OHRI / uOttawa / CHEO** — Ottawa-specific research partnerships.

## Open questions

- Reference EHR integration for testing — do we partner with Epic (via Cosmos-style API) or build against FHIR-only?
- Model registry — extend MLflow, or build on OCI/Docker distribution?
- Confidential compute — support NVIDIA H100 CC only, or also SGX/SEV?
- Edge target — Jetson Orin only, or also Coral, Hailo, Raspberry Pi?
- Canadian biology AI partnerships — which lab first? (Mila, Vector, Deep Genomics, AbCellera)
- Sovereign deployment infrastructure — host on Alliance Canada, commercial cloud (Canadian regions), or self-hosted by institutions?

## Contributing

Open to collaborators. The substrate is too big for any one team. Reach out via issues on this repo.

## Founder

Built by a Personal Support Worker in Ottawa with 10 years of nursing experience (facility + home care), currently employed at Gary J Armstrong Retirement Home. Domain expertise: PSW workflows, retirement-home operations, Ontario LTC regulation, frontline senior care. Engineering collaboration via AI-augmented development.

## License

Apache 2.0 — open source, benefit everyone.

## Generative biology AI layer (added 2026-06-28)

In addition to clinical AI + biology AI **analysis**, openclinical-ai now includes a **generative biology AI layer** — for designing new proteins, RNA, DNA from scratch.

### The wedge

The Canadian generative biology AI gap is wider than the analysis gap:

- **No Canadian company** ships generative biology AI foundation models.
- **All major players** are foreign: Generate Biomedicines ($370M+ US), Cradle (EU), Profluent (US), EvolutionaryScale ($142M US, AI21 spinoff), Iambic (US), Isomorphic (UK/Alphabet).
- **Canadian biotech (AbCellera, Deep Genomics)** does target identification + screening, not generative biology per se.
- **openclinical-ai** is positioned to be the first open, sovereign Canadian generative biology substrate.

### What we ship

| Component | Purpose |
|---|---|
| `runtime/bio_security.py` | Mandatory biosecurity screening on every generated sequence — 5 layers (pathogen signatures, toxin motifs, AI-evasion patterns, length sanity, composition). IGS-compliant. |
| `biology_ai/generation/adapters.py` | Stubs for RFdiffusion (Baker lab, BSD), ProteinMPNN (Baker lab, BSD), ESM-3 (EvolutionaryScale, Apache 2.0), Bindcraft (Baker lab, BSD), ProGen (Profluent/Salesforce, Apache 2.0). |
| `/v1/generate/{protein,binder,rna,dna}` | Multi-tenant endpoints for generative biology, biosecurity-gated. |
| `/v1/synthesis/order` | Push designs to Twist, IDT, GenScript with biosecurity verification attached. |
| `/v1/biosecurity/audit` | Tenant-scoped biosecurity screening audit log. |

### Why biosecurity at the substrate level

Per [Science 2025](https://www.science.org/doi/10.1126/science.adu8578): "current screening practices at DNA synthesis providers — largely reliant on sequence similarity to known biological threats — are increasingly inadequate" against AI-redesigned protein sequences.

openclinical-ai enforces multi-layer biosecurity screening **at the substrate level**, before generated sequences reach synthesis vendors. Every generated protein/DNA/RNA is screened through 5 layers and blocked if risk_score > 0.7.

### Market best points applied

| Best point from the market | Applied in openclinical-ai |
|---|---|
| Foundation models with fine-tuning | Signed manifest registry for ESM Cambrian, ProteinMPNN, RFdiffusion |
| Multi-modal generation | `inputs.constraints` accepts sequence motifs + structure + function |
| Wet-lab integration | `/v1/synthesis/order` for Twist, IDT, GenScript |
| API-first design | REST endpoints for every operation |
| Mandatory biosecurity screening | Substrate-level, non-optional |
| Open weights where possible | Prioritize BSD + Apache 2.0 open weights (Baker lab, Profluent, EvolutionaryScale) |
| Specific modalities | Start with protein (ProteinMPNN), binder (Bindcraft), RNA (future), DNA (stub ESM-3) |
| Sovereign training + inference | TamIA / Nibi / Trillium integration planned |
| Provenance + audit for every design | `GenerationOutput.biosecurity` + audit_event_id |
| Pre-clinical regulatory pathway | Biosecurity audit logs + provenance manifests as foundation |

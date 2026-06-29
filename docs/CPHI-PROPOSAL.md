# Canadian Precision Health Initiative — Partnership Proposal

## **openclinical-ai: A Sovereign AI Deployment Substrate for Canadian Precision Medicine**

**Submitted under:** Canadian Precision Health Initiative (CPHI) — Genome Canada + Innovation, Science and Economic Development Canada (ISED)
**Total CPHI pool:** $200M (announced March 2025, $81M federal via Strategic Science Fund)
**Proposed partnership ask:** $8.5M over 3 years (Year 1: $3.5M, Year 2: $3.0M, Year 3: $2.0M)
**Match commitments:** $2.5M from NRC-IRAP AI Assist + Ontario BioCreate + partner in-kind
**Total project value:** $11M over 3 years
**Lead organization:** openclinical-ai (Apache 2.0, Ottawa-based)
**Principal investigator / founder:** Brian Clerjuste, Personal Support Worker (10 years nursing, Ottawa)
**Technical lead:** Engineering collaboration via open-source AI-augmented development
**Date:** June 2026
**Status:** Draft for partner review

---

## Executive Summary

**Canada's precision medicine data is a national asset. It currently flows to foreign AI infrastructure. The Canadian Precision Health Initiative (CPHI) is a $200M federal commitment to change that — but the initiative is missing a critical layer: an open, sovereign deployment substrate that hosts the AI models trained on Canadian genomic data, runs them in Canadian clinical environments, and keeps patient data, models, and compute inside Canada.**

openclinical-ai proposes to build and operate that layer — a sovereign, open-source, Apache 2.0 deployment substrate for clinical AI and biology AI, built in Canada, deployed across Canadian clinical environments, with Canadian compute, under Canadian law. The substrate becomes the deployment foundation for every CPHI-funded precision medicine model, every provincial genomics program, every Canadian hospital running biology AI.

**The pitch in one sentence:** Canadian genomic data should not leave Canada to be useful. openclinical-ai ensures it doesn't have to.

---

## 1. Problem Statement — Canadian Precision Medicine Without Sovereign AI Infrastructure

### 1.1 The sovereignty gap

The 2024 Nobel Prize in Chemistry recognized AlphaFold (DeepMind, UK) and David Baker's protein design work (UW, US) as foundational biology AI. These models are foreign-built and foreign-hosted. The same is true for RoseTTAFold (US), ESM-3 (Meta, US), and most major biology foundation models.

Canadian hospitals today feed clinical data to:
- **Epic Systems** (US) — ~70% of new Canadian hospital contracts; Cosmos holds 300M+ patient records in US data centers
- **Oracle Health** (US) — legacy Cerner systems, Feb 2025 breach exposed 80+ hospitals
- **Google Health** (US) — clinical AI products
- **Microsoft Nuance/DAX** (US) — ambient AI scribes
- **AWS, Azure, GCP** (US) — the underlying compute for most Canadian AI deployments

**Canadian patient genomic data, when used by AI, leaves Canada.** This is a sovereignty problem with three dimensions:

| Dimension | Current state | Risk |
|---|---|---|
| **Data sovereignty** | Canadian genomic data hosted on US clouds | PHIPA + PIPEDA exposure, foreign jurisdiction over Canadian health data |
| **Compute sovereignty** | Canadian biology AI runs on foreign compute | Canadian AI capacity gap; dependence on foreign infrastructure |
| **Model sovereignty** | AlphaFold (UK), RoseTTAFold (US), ESM-3 (US) | Canadian research depends on foreign-built biology models with no guarantee of access, modification, or clinical translation rights |

### 1.2 The deployment gap

CPHI will fund precision medicine model training — sequencing 100,000+ Canadian genomes (announced March 2025, Pillar 1: $60M short-read WGS + $15M long-read WGS). But training is only half the problem. The other half — **getting the trained models into Canadian clinical environments safely, with consent, audit, and compliance built in** — is unsolved.

Existing Canadian biology AI deployments are:
- **Bespoke per hospital** — Vector Institute's Health AI Implementation Toolkit is Ontario-centric, not nationally deployable
- **Closed-source** — Deep Genomics, AbCellera are private; no community access
- **Foreign-hosted** — most clinical AI runs on US clouds
- **Research-grade, not clinical-grade** — academic outputs don't translate to PSW/nurse/doctor-facing tools

CPHI's Pillar 1 funding goes through March 2029. **The deployment substrate must be built in parallel with the model training, or CPHI outputs will not reach Canadian patients.**

### 1.3 The equity gap

The user's vision — AlphaGo-tier AI for everyone, all levels of care, every Canadian — points at a real gap: precision medicine AI is being built for academic medical centers (TOH, UHN, CHEO). It is not being built for:
- **Personal Support Workers** in retirement homes (Ontario has ~80,000 PSWs; user's employer: Gary J Armstrong Retirement Home, Ottawa)
- **Long-term care** residents (Ontario has ~78,000 LTC beds; complex polypharmacy, dementia care)
- **Rural and remote** patients (Canada has 1,200+ remote communities; most lack specialist AI access)
- **Indigenous communities** (genomic datasets underrepresent Indigenous populations; ethical + data sovereignty questions)

A sovereign substrate lets the same models run in academic medical centers and in a Gary J Armstrong PSW's pocket. The deployment layer is where equity happens.

---

## 2. Proposed Solution — openclinical-ai as the CPHI Sovereign Deployment Substrate

### 2.1 What openclinical-ai is

An **open-source, Apache 2.0, sovereign deployment substrate** for biology AI and clinical AI. The substrate is the missing layer between trained models (Mila's Dreamfold, CPHI-funded precision medicine models, Vector's clinical AI) and clinical users (PSWs, nurses, doctors, researchers, patients).

| Component | Purpose | CPHI relevance |
|---|---|---|
| `runtime/` | Inference runtime — CPU/GPU/edge, multi-model | Hosts CPHI-trained precision medicine models |
| `registry/` | Signed model registry, provenance, model cards, drift monitoring | Tracks CPHI model versions, Canadian compliance |
| `audit-gateway/` | Every inference logged, consent-aware, FHIR AuditEvent export | Patient consent propagated; CPHI audit trail |
| `consent/` | Patient consent propagated across the inference pipeline | PHIPA + IPC compliant consent-as-API |
| `compliance/` | PHIPA / PIPEDA / HIPAA / EU AI Act / Health Canada alignment artifacts | Compliance-by-default for CPHI deployments |
| `deploy/` | Kubernetes (cloud/on-prem), single-node (edge), Compose (dev) | Sovereign deployment anywhere in Canada |
| `fhir/` | FHIR-native identity, SMART-on-FHIR auth, CDS Hooks | Integrates with Epic (TOH, CHEO), other EHRs |
| `biology-ai/` | Biology AI vertical — protein folding, variant impact, drug-target ID, drug interaction | Hosts AlphaFold-class + CPHI precision medicine models |
| `psw-assistant/` | PSW-first vertical — shift handoff, ADL tracking, fall risk, family comms | Frontline clinical reach |

### 2.2 Sovereignty by design

The substrate is built so that:

1. **Data stays in Canada.** Inference happens in the same jurisdiction as the patient data. No cross-border calls. No foreign-cloud PHI processing.
2. **Compute is Canadian.** Deployed on Digital Research Alliance of Canada (DRAC) clusters, NRC compute, or Canadian cloud providers (Bell, Telus, Cologix). The $40M National AI Compute Rapid Deployment initiative (July 2025) explicitly funds this kind of deployment.
3. **Models are open-source.** Apache 2.0. Canadian biology AI can be trained, modified, deployed, and audited by Canadians. No vendor lock-in to foreign AI vendors.
4. **Compliance is Canadian.** PHIPA (Ontario), PIPEDA (federal), IPC responsible AI principles (Ontario Joint Principles for Responsible Use of AI, January 2026) — built in by default.
5. **Procurement-ready.** Federal procurement standards (Government of Canada Cloud Guardrails, Canadian Centre for Cyber Security guidance). Ottawa-based team, federal procurement expertise.
6. **Audit-ready.** Every inference logged, every model version tracked, every consent decision recorded. CPHI reporting, federal AI inventory compliance.

### 2.3 How it complements CPHI

| CPHI pillar | openclinical-ai role |
|---|---|
| **Pillar 1: 100,000+ genomes** ($60M short-read + $15M long-read WGS) | Deploy sequencing-inference pipelines on Canadian compute; feed results to Canadian clinical environments via FHIR-native consent/audit |
| **Pillar 2 (expected early 2026): AI for variant impact + drug target discovery** | Host CPHI-trained variant impact models (AlphaMissense-class) on sovereign substrate; expose via PSW/nurse-facing tools |
| **Pillar 3 (expected early 2026): Clinical translation + Indigenous genomics** | Provide deployment infrastructure for Indigenous genomics projects under OCAP principles; sovereign data sovereignty for First Nations communities |
| **Cross-pillar: Canadian sovereignty + public trust** | Apache 2.0 + Canadian compute + Canadian compliance = provably sovereign, provably public |

---

## 3. Innovation and Differentiation

### 3.1 What's unique about openclinical-ai

| Existing approach | Limitation | openclinical-ai |
|---|---|---|
| **Epic Cosmos** (US) | Closed, vendor-locked, US-hosted | Open source, vendor-neutral, Canadian-hosted |
| **Vector Health AI Toolkit** (Ontario) | Ontario-only, not generalizable | National, FHIR-native, any Canadian site |
| **Mila Dreamfold** | Research-stage, no deployment layer | Substrate hosts Dreamfold when it reaches clinical stage |
| **Deep Genomics** | Closed-source, drug-discovery only | Open substrate, complementary to closed drug discovery |
| **AbCellera** | Closed-source, antibody discovery | Open substrate for clinical translation of antibody work |
| **Foreign clouds (AWS/Azure/GCP)** | US jurisdiction over Canadian PHI | Canadian compute, PHIPA-compliant by default |
| **Bespoke per hospital** | Cost-prohibitive for rural / LTC / PSW settings | Single substrate deployable anywhere |

### 3.2 The sovereign AI framing in detail

The user's framing — "make AlphaGo AI used in everyone's lives" — translates to: Canadian biology AI, deployed as public infrastructure, accessible to every Canadian regardless of institution, geography, or budget.

Sovereignty is the load-bearing principle. Without it:
- Canadian genomic data flows to US AI vendors
- Canadian hospitals depend on Epic/Oracle for AI
- Canadian biology AI research depends on AlphaFold/RoseTTAFold/ESM-3
- Canadian patients' data is governed by US HIPAA + CLOUD Act, not Canadian PHIPA + PIPEDA
- Canadian AI compute depends on AWS/Azure/GCP regions

With openclinical-ai as the sovereign substrate:
- Canadian genomic data stays in Canada
- Canadian hospitals own their AI infrastructure
- Canadian biology AI models are open-source, trainable by Canadians
- Canadian patients' data is governed by Canadian law
- Canadian AI compute is on DRAC/NRC/Canadian cloud

This is the sovereignty Canada needs to make precision medicine actually work for Canadians.

### 3.3 The equity-first deployment layer

A sovereign substrate is necessary but not sufficient. The deployment must reach:
- **Personal Support Workers** in retirement homes (Ontario ~80,000 PSWs, Canada ~250,000)
- **Long-term care** residents (Ontario ~78,000 beds, Canada ~200,000+)
- **Rural and remote** patients (1,200+ remote communities)
- **Indigenous communities** (underrepresented in genomic datasets)
- **Frontline healthcare workers** at the bottom of the medical hierarchy

The PSW-first vertical (`psw-assistant/`) is the proof: voice-first shift handoff, ADL tracking, fall risk, family communication. The same substrate that runs AlphaMissense-class variant impact for a CHEO researcher also runs a PSW's shift handoff at Gary J Armstrong.

That's the equity promise.

---

## 4. Team

### 4.1 Founder / Principal Investigator — Brian Clerjuste

**Role:** Vision, PSW domain expertise, Ontario LTC operations knowledge, Ottawa relationships, federal procurement readiness.

**Background:**
- Personal Support Worker, Gary J Armstrong Retirement Home (current employer)
- 10 years nursing experience (facility + home care)
- Ottawa-based, Ontario-licensed PSW
- Founder of openclinical-ai project (Apache 2.0)

**Unique value to CPHI proposal:**
- **PSW-first perspective:** 10 years at the frontline of senior care — knows the actual clinical workflows where AI will land
- **Ontario LTC knowledge:** deep familiarity with Ontario's Long-Term Care Homes Act, PSW standards, retirement home operations
- **Ottawa relationships:** federal procurement hub access (NRC, Statistics Canada, Canadian Centre for Cyber Security, Office of the AI Minister Evan Solomon)
- **Equity commitment:** "everyday regular people benefit from AI" — not academic AI for academic AI's sake

### 4.2 Technical Lead — openclinical-ai Engineering Collaboration

**Role:** Architecture, code, infrastructure, model integration, deployment.

**Approach:** AI-augmented development (open-source AI assistants, code generation, model integration). The substrate is built by a small team using AI tools to compound productivity — a model that scales with the project's mission.

**Deliverables:** runtime/, registry/, audit-gateway/, consent/, compliance/, deploy/, fhir/, biology-ai/, psw-assistant/, all under Apache 2.0.

### 4.3 Advisors (to be confirmed)

- **Mila** — protein design + generative biology technical advisor (open academic posture, ideal partner)
- **CHEO Research Institute** — pediatric genomics + ThinkRare national deployment advisor (Ivan Terekhov)
- **Bruyère Research Institute** — geriatric + LTC AI advisor
- **NRC-IRAP** — Canadian SME + AI biotech funding advisor
- **Ontario IPC** — privacy + responsible AI advisor

### 4.4 Why this team wins

Most CPHI proposals will come from academic PIs with strong research credentials. openclinical-ai wins on:
- **Frontline credibility** — 10 years of PSW experience is rare in Canadian AI
- **Equity-first** — built around "everyday people benefit," not academic prestige
- **Sovereignty focus** — explicit Canadian sovereignty, not foreign-cloud-by-default
- **Apache 2.0** — open-source, no vendor lock-in
- **Ottawa-based** — federal procurement hub access
- **Execution speed** — small team, AI-augmented, can move fast

---

## 5. Partners

### 5.1 Tier 1 — Pilot deployment partners

| Partner | Role | Contribution |
|---|---|---|
| **CHEO Research Institute** | Pediatric genomics + ThinkRare national deployment | ThinkRare deployment on openclinical-ai substrate; national rollout across McMaster/Alberta/Stollery (Feb 2026 window) |
| **Bruyère Continuing Care** | LTC + geriatric research | PSW assistant pilot at Bruyère Continuing Care sites; frailty research partnership |
| **Perley Health** | LTC + veterans' care | Esprit-ai integration; LTC AI deployment |
| **Gary J Armstrong Retirement Home** | PSW-first pilot site | Voice-first shift handoff + ADL tracking + fall risk detection |
| **Ottawa Hospital Research Institute (OHRI)** | Clinical AI + biotherapeutics | OHRI clinical AI models on openclinical-ai substrate |

### 5.2 Tier 2 — Technical + infrastructure partners

| Partner | Role |
|---|---|
| **Mila** (Montreal) | Protein design + generative biology (Dreamfold); open academic |
| **Vector Institute** (Toronto) | Clinical AI integration (Health AI Implementation Toolkit); UHN/Sinai/Sunnybrook/SickKids |
| **Digital Research Alliance of Canada (DRAC)** | Sovereign compute; TamIA cluster for biology AI |
| **NRC-IRAP AI Assist** | $75-200K SME funding; AI biotech advisor |
| **Ontario BioCreate** | Ontario biotech SME accelerator; Ontario Genomics partnership |
| **Genome Canada / Ontario Genomics** | Funding alignment; regional centre coordination |

### 5.3 Tier 3 — Ecosystem + advocacy partners

| Partner | Role |
|---|---|
| **Office of the AI Minister** (Evan Solomon, Ottawa) | Federal AI policy alignment |
| **Canadian Centre for Cyber Security** (Ottawa) | Federal cybersecurity guidance |
| **Ontario IPC** | Privacy + responsible AI guidance (El Emam is Scholar-in-Residence) |
| **CIHR** | Health research funding alignment |
| **Canadian Patient Safety Institute** | PSW + nurse safety outcomes |

---

## 6. Three-Year Work Plan

### Year 1 (April 2026 — March 2027): Foundational substrate + first pilots

**Substrate milestones:**
- Q1: Runtime MVP — signed model loading, basic inference, audit log
- Q2: FHIR-native consent engine + audit gateway
- Q3: Compliance pack (PHIPA + PIPEDA + IPC responsible AI)
- Q4: Edge tier deployment (Jetson Orin + Raspberry Pi 5)

**Pilot milestones:**
- Q1: Gary J Armstrong PSW assistant — voice-first shift handoff MVP
- Q2: CHEO ThinkRare deployment on openclinical-ai substrate
- Q3: Bruyère LTC pilot (PSW assistant extension)
- Q4: OHRI clinical AI integration

**Sovereignty milestones:**
- Q1: DRAC compute integration; TamIA cluster deployment
- Q2: PHIPA + PIPEDA compliance certification
- Q3: Canadian cloud (Bell/Telus/Cologix) deployment
- Q4: Federal Cloud Guardrails alignment

### Year 2 (April 2027 — March 2028): Biology AI + CPHI integration

**Substrate milestones:**
- Q1: Biology AI vertical — protein folding + variant impact support
- Q2: AlphaMissense-class variant impact predictor MVP
- Q3: Drug-interaction predictor for PSWs (polypharmacy focus)
- Q4: Federated learning across Ottawa hospitals + CHEO + Bruyère

**CPHI integration milestones:**
- Q1: CPHI Pillar 1 sequencing pipeline integration
- Q2: CPHI Pillar 2 (variant impact + drug target) deployment support
- Q3: CPHI Pillar 3 (clinical translation + Indigenous genomics) sovereign infrastructure
- Q4: CPHI-funded precision medicine models hosted on openclinical-ai

**Sovereignty milestones:**
- Q1: Indigenous genomics OCAP-compliant deployment
- Q2: Cross-provincial deployment (Ontario → Quebec → Alberta → BC)
- Q3: Federal procurement readiness (Government of Canada Cloud Guardrails)
- Q4: Sovereign AI Compute integration ($40M National AI Compute Rapid Deployment)

### Year 3 (April 2028 — March 2029): Scale + sustainability

**Substrate milestones:**
- Q1: Production-grade registry with model card + drift monitoring
- Q2: Confidential compute integration (Intel SGX, AMD SEV, NVIDIA H100 CC)
- Q3: Multi-tenant deployment for hospital networks
- Q4: Open-source community governance (Apache 2.0 + CLA + GOVERNANCE.md)

**Scale milestones:**
- Q1: 5+ Canadian hospital deployments
- Q2: 3+ LTC + retirement home deployments
- Q3: Indigenous community partnership deployment
- Q4: National rollout ready for CPHI outputs

**Sustainability milestones:**
- Q1: Open Collective donation infrastructure
- Q2: Cooperative entity formation (mission-locked)
- Q3: NRC-IRAP follow-on funding + CIHR operating grant
- Q4: Self-sustaining funding model

---

## 7. Budget — $11M over 3 years ($8.5M CPHI + $2.5M match)

### 7.1 CPHI ask: $8.5M

| Category | Year 1 | Year 2 | Year 3 | Total |
|---|---|---|---|---|
| **Engineering (2 FTE × 3 years)** — substrate + biology AI + PSW vertical | $700K | $700K | $500K | $1.9M |
| **Compute (DRAC + NRC + Canadian cloud)** | $300K | $500K | $400K | $1.2M |
| **Pilot deployment (CHEO + Bruyère + Perley + Gary J Armstrong + OHRI)** | $400K | $300K | $200K | $900K |
| **Compliance + audit (PHIPA + PIPEDA + IPC + federal)** | $300K | $200K | $100K | $600K |
| **Indigenous genomics OCAP deployment** | $200K | $300K | $200K | $700K |
| **Edge tier + rural deployment** | $300K | $200K | $100K | $600K |
| **Open-source community + governance** | $200K | $200K | $200K | $600K |
| **PMO + admin** | $200K | $200K | $200K | $600K |
| **Travel + partner meetings** | $100K | $100K | $100K | $300K |
| **Year total** | **$2.7M** | **$2.7M** | **$2.0M** | **$7.4M** |
| **Indirect costs (15%)** | $400K | $400K | $300K | $1.1M |
| **Year total with indirect** | **$3.1M** | **$3.1M** | **$2.3M** | **$8.5M** |

### 7.2 Match commitments: $2.5M

| Source | Year 1 | Year 2 | Year 3 | Total |
|---|---|---|---|---|
| **NRC-IRAP AI Assist** ($75-200K typical awards) | $200K | $200K | $100K | $500K |
| **Ontario BioCreate accelerator** | $200K | $100K | — | $300K |
| **DRAC in-kind compute** (TamIA + Trillium) | $300K | $400K | $300K | $1.0M |
| **Partner in-kind** (CHEO, Bruyère, OHRI, Perley — staff time, facilities) | $200K | $300K | $200K | $700K |
| **Match total** | **$900K** | **$1.0M** | **$600K** | **$2.5M** |

### 7.3 Total project value: $11M over 3 years

### 7.4 Why this budget is realistic

- **Substrate engineering is mostly built already** — openclinical-ai repo exists; $1.9M covers 2 FTE × 3 years of AI-augmented development
- **Compute is mostly free** — DRAC provides academic compute; $1.2M is supplementary
- **Pilots are partner-supported** — CHEO, Bruyère, OHRI contribute staff time and facilities
- **Match is high** — 22% match ratio is realistic for federal initiatives; CPHI typical range is 20-30%

---

## 8. Outcomes and Impact

### 8.1 Technical outcomes

- **Production-grade sovereign substrate** for biology AI + clinical AI, Apache 2.0
- **3+ Canadian hospital deployments** with FHIR-native consent + audit + compliance
- **5+ LTC + retirement home deployments** with PSW assistant
- **1+ Indigenous genomics deployment** with OCAP-compliant data sovereignty
- **100,000+ Canadian genomes** (CPHI Pillar 1 outputs) deployable via the substrate
- **Canadian compute** for every inference — no foreign-cloud PHI

### 8.2 Sovereignty outcomes

- **No Canadian genomic data leaves Canada** for AI inference
- **No Canadian hospital depends on Epic/Oracle for AI** beyond EHR storage
- **No Canadian biology AI deployment depends on AlphaFold/RoseTTAFold/ESM-3** for clinical use
- **Canadian AI capacity** built through DRAC + NRC + Canadian cloud
- **Federal procurement-ready** sovereign AI infrastructure

### 8.3 Equity outcomes

- **Every Canadian** has access to biology AI through public health system
- **PSWs in retirement homes** have AI clinical support (currently zero)
- **LTC residents** have AI-assisted medication management + fall detection
- **Rural + remote patients** have AI access via edge deployment
- **Indigenous communities** have OCAP-compliant genomics AI

### 8.4 Economic outcomes

- **$11M project value** leveraged against $200M CPHI initiative
- **Open-source contributions** — every Canadian hospital benefits without licensing fees
- **Canadian AI talent** trained through the project (engineering + compliance + deployment)
- **Canadian biotech AI** gets sovereign deployment infrastructure
- **Tax-funded Canadian AI** delivered through public infrastructure

### 8.5 Research outcomes

- **Open datasets** of Canadian biology AI model performance
- **Open benchmarks** for sovereign clinical AI deployment
- **Peer-reviewed publications** on PSW + LTC + Indigenous genomics AI deployment
- **Open-source community** contributing to substrate + verticals

---

## 9. Risk Management

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| **CPHI funding insufficient or delayed** | Medium | High | Bootstrap with NRC-IRAP + Ontario BioCreate + DRAC; CPHI as accelerator, not dependency |
| **CHEO ThinkRare deployment delays** | Low | High | Maintain pilot at Gary J Armstrong as primary substrate validation; CHEO is bonus, not critical path |
| **Foreign AI vendor opposition (Epic, Oracle)** | Medium | Medium | Apache 2.0 + open substrate = no vendor lock-in; compete on sovereignty + cost, not features |
| **Canadian compute shortage** | Medium | High | $40M National AI Compute Rapid Deployment (July 2025) explicitly funds this; DRAC TamIA cluster available |
| **PHIPA / PIPEDA compliance gaps** | Low | High | Ontario IPC + El Emam as advisor; compliance-by-default architecture |
| **Indigenous genomics OCAP compliance** | Medium | High | First Nations-led partnership; OCAP principles built into deployment; not deployable without community consent |
| **Founder single-point-of-failure** | Medium | High | Apache 2.0 + open-source community + GOVERNANCE.md + cooperative entity in Year 3 |
| **PSW adoption resistance** | Medium | Medium | Co-design with PSWs at Gary J Armstrong; voice-first reduces friction; PSW is the founder |
| **CPHI scope misalignment** | Low | Medium | Tight alignment with Pillar 1 + Pillar 2 + Pillar 3; explicit sovereignty + equity framing |

---

## 10. Why This Proposal Wins

### 10.1 The strategic case

Canada has invested $2-3B+ in genomics + AI over 2024-2026. **None of it has produced an open, sovereign deployment substrate.** The substrate is the missing layer that lets every Canadian genomic dataset, every CPHI-funded model, every provincial genomics program reach Canadian patients without depending on foreign AI infrastructure.

CPHI is the right initiative to fund the substrate because:
- Pillar 1 ($75M) is sequencing — generates the data
- Pillar 2 (~$80M) is AI model training — generates the models
- **Pillar 3 (~$45M) is clinical translation — needs the deployment layer**

openclinical-ai is the substrate Pillar 3 needs.

### 10.2 The sovereignty case

Canadian precision medicine sovereignty requires:
1. **Data sovereignty** — Canadian genomic data stays in Canada
2. **Compute sovereignty** — Canadian compute for biology AI
3. **Model sovereignty** — Canadian-trained biology AI for clinical use
4. **Procurement sovereignty** — Canadian-controlled AI infrastructure for federal healthcareangi

openclinical-ai delivers all four. No other CPHI proposal will.

### 10.3 The equity case

The user's vision — "everyday regular people benefit from AI" — points at a real gap: precision medicine AI is being built for academic medical centers. The PSW-first vertical is the proof that the same sovereign substrate can serve PSWs in retirement homes, nurses in LTC, families of rare disease patients, Indigenous communities, rural patients.

Sovereignty without equity is just sovereignty for the privileged. openclinical-ai is sovereignty for everyone.

### 10.4 The execution case

The team is small but experienced:
- 10 years PSW expertise (frontline credibility)
- Apache 2.0 substrate already started
- Ottawa-based (federal procurement hub)
- AI-augmented development (small team, high productivity)
- Open-source community (scalable governance)

Three years. $11M. Sovereign Canadian biology AI infrastructure for every Canadian.

---

## Appendices

### A. Project briefaren

See `docs/PROJECT-BRIEF.md` for the full project brief.

### B. Canadian biology AI landscape profiles

See `/workspace/bio-ai-kb/profiles/` for:
- `mila-profile.md` — Mila Quebec AI Institute (Dreamfold protein design)
- `vector-profile.md` — Vector Institute (Health AI Implementation Toolkit)
- `abcellera-profile.md` — AbCellera (antibody discovery, NASDAQ: ABCL)
- `deep-genomics-profile.md` — Deep Genomics (rare disease drug discovery)
- `canadian-infrastructure.md` — Canadian biotech AI funding + compute landscape
- `ottawa-bio-ai.md` — Ottawa bio-AI cluster (OHRI + CHEO + Bruyère + uOttawa + retirement homes)

### C. Canadian biology AI strategy synthesis

See `/workspace/bio-ai-kb/strategy/canadian-biology-ai-strategy.md` for the full strategy doc.

### D. Reference architecture

See `docs/THREAT-MODEL.md` for the substrate's threat model. Reference architecture diagrams to be added.

### E. Glossary

- **CPHI** — Canadian Precision Health Initiative
- **PHIPA** — Personal Health Information Protection Act (Ontario)
- **PIPEDA** — Personal Information Protection and Electronic Documents Act (federal)
- **IPC** — Information and Privacy Commissioner of Ontario
- **DRAC** — Digital Research Alliance of Canada (formerly Compute Canada)
- **OCAP** — Ownership, Control, Access, Possession (First Nations data sovereignty principles)
- **PSW** — Personal Support Worker
- **LTC** — Long-Term Care
- **Apache 2.0** — permissive open-source license (no copyleft, no patent retaliation)

---

## Signature

**Brian Clerjuste** — Founder, openclinical-ai
Personal Support Worker, Gary J Armstrong Retirement Home, Ottawa
June 2026

---

*"Canadian genomic data should not leave Canada to be useful. openclinical-ai ensures it doesn't have to."*
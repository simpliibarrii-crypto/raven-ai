# Raven Ecosystem Operations

Raven should grow like a product ecosystem, not a pile of demos. The next direction is unified operations first, growth second.

## North Star

Raven AI is the flagship biology and healthcare agent platform. The ecosystem should make scientific and clinical AI outputs cheaper to run, easier to inspect, and safer to review.

The current growth message:

> Raven AI is local-first scientific AI infrastructure for biology, clinical workflows, agent orchestration, evidence provenance, and token-efficient reasoning.

## Product Roles

| Surface | Role | Primary user | Near-term job |
|---|---|---|---|
| Raven AI | Core runtime, Evidence Graph, Token Economy, architecture docs | Builders, researchers, technical evaluators | Become the source of truth and shared contracts repo |
| Home for AI | Desktop/local command center | User/operator | Show local runs, traces, model routing, and connector evidence |
| OpenClinical AI | Clinical workflow substrate | PSW, nurse, care team, clinical builder | Attach consent-gated evidence traces to shift handoff and audit flows |
| Hermes Edge | Local/mobile/edge runtime | Mobile and edge AI builder | Provide local-small/local-large lanes and benchmark proof for token savings |

## What To Do Next

### 1. Review and unify all projects

This comes before aggressive growth. The repos need to feel like one product family.

Done means:

- Every repo has a clear role and points back to Raven AI.
- Every repo documents how it uses `raven.evidence_graph.v1`.
- Every repo documents how it should use Raven Token Economy.
- CI runs on pull requests and protects against broken demos.
- Public docs avoid unsupported production, financial, medical-device, or crypto-token claims.
- Demo surfaces work on mobile, tablet, and desktop without Replit/generator branding.

### 2. Make one polished public demo

The flagship demo should show one end-to-end workflow:

1. Add sources.
2. Extract or write claims.
3. Build an answer trace.
4. Show the Token Economy plan: cache reuse, draft lane, confidence floor, verification spans, and saved context tokens.
5. Export `raven.evidence_graph.v1` JSON.
6. Show how the packet flows into Home for AI, OpenClinical AI, and Hermes Edge.

### 3. Add real adapters one at a time

Avoid adding broad AI features until the contracts are stable.

Recommended order:

1. Home for AI: local run records with evidence trace IDs and token economy decisions.
2. OpenClinical AI: consent-gated PSW handoff trace adapter.
3. Hermes Edge: benchmark-to-evidence adapter plus local route/token-savings report.
4. Raven AI: shared package exports and examples that sibling apps can import or copy safely.

### 4. Grow around credibility

Raven should attract technical users by showing restraint:

- No fake benchmark claims.
- No unsupported medical claims.
- No broad “AI for everything” language.
- No crypto-token confusion around Token Economy.
- Public demos must explain exactly what is real, what is local, and what is experimental.

## Unified Operation Rules

### Evidence rule

Every meaningful output should be traceable to sources and claims. If an output cannot explain its source trail, it is not ready for a serious workflow.

### Token rule

Every expensive model call should justify itself. Raven should prefer cache, tools, local lanes, narrow retrieval, and selective verification before escalation.

### Privacy rule

PHI, private user files, credentials, unpublished strategy, and sensitive clinical notes stay local or inside an approved deployment boundary.

### Benchmark rule

No speed, cost, memory, or quality claim ships without device/backend/context evidence.

### Demo rule

A demo is publishable only when it works on desktop, tablet, and mobile, has no visible platform branding, has no dead links, and contains no obvious placeholder IDs.

## Immediate Backlog

| Priority | Work | Repo |
|---|---|---|
| P0 | Add Token Economy explanation to the public Evidence Graph demo without crypto-token language | Replit demo / Raven AI docs |
| P0 | Fix README Evidence Graph quickstart to use the actual `kind` argument instead of `source_type` | Raven AI |
| P1 | Add Token Economy integration docs to Home for AI, OpenClinical AI, and Hermes Edge | sibling repos |
| P1 | Add issue backlog for evidence trace adapters and token economy adapters | all repos |
| P1 | Confirm CI status and make failing checks actionable instead of silent | all repos |
| P2 | Add a clean “Raven Ecosystem Demo Script” for X, LinkedIn, Hugging Face, and GitHub releases | Raven AI |
| P2 | Add benchmark/result schema for Hermes Edge local token savings | Hermes Edge |

## Growth Direction

Head toward **Raven Trust Runtime**:

- Evidence Graph = why an answer should be trusted.
- Token Economy = why the system spent only the necessary tokens.
- Hermes Edge = where private/local work runs.
- Home for AI = where users control workflows.
- OpenClinical AI = where clinical workflows get consent, audit, and review boundaries.

This is stronger than another generic chatbot. It gives Raven a moat: trust, cost discipline, local-first design, and clinical/scientific caution.

# Raven Agentic Lab Loop: A Connector-Receipt Contract for Auditable AI Science

## Abstract

Modern scientific AI systems need more than fluent reasoning. They need closed-loop execution: a question becomes a hypothesis, a plan becomes a run, a run becomes evidence, evidence becomes a gated claim, and the claim becomes a reproducible public artifact only when receipts exist. We introduce the Raven Agentic Lab Loop, a lightweight software contract for representing multi-agent scientific work across GitHub, Linear, Vercel, Replit, Hugging Face, and MCP registry surfaces. The first implementation adds `SubagentSpec`, `ConnectorReceipt`, and `LabLoopRun` objects that compile into Raven's existing `ScientificRunManifest` and are evaluated by Scientific Agent Gates. Initial connector diagnostics show GitHub, Linear, Vercel, Hugging Face, and MCP registry access working, while Replit app-agent inspection is paused. These results support a narrow claim: Raven can now represent and gate software-side agentic lab-loop records. They do not support claims of autonomous therapeutic discovery, wet-lab validation, or production clinical deployment.

## 1. Motivation

Capable's careers page describes a future involving rapid in-house data generation, ever-improving ML models, same-day synthesis-to-testing iterations for therapeutics, and collapsing the loop between research, synthesis, and testing. Raven's current scope is software infrastructure, not wet-lab operation. The goal is therefore to implement the recordkeeping and verification substrate needed before any stronger closed-loop science claim is made.

The problem is not simply whether an AI can write code. The problem is whether every step of a scientific-agent workflow can be replayed, challenged, measured, routed safely, and described without exaggeration.

## 2. System design

The implementation introduces three core objects.

`SubagentSpec` defines a narrow worker role with objective, required evidence, and escalation trigger. The default board includes twelve roles: intake, hypothesis, planning, execution, evidence, verification, safety, metrics, deployment, paper, distribution, and red-team review.

`ConnectorReceipt` records work done through an external surface. Each receipt contains a surface name, status, summary, evidence strings, optional measurement time, and notes. Receipts can be transformed into Evidence Graph-compatible sources.

`LabLoopRun` captures the full run: question, hypothesis, workflow stage, risk, subagents, connector receipts, claims, metrics, token-economy metadata, evidence trace, code artifacts, output artifacts, replay command, environment fingerprint, and safety flags.

The adapter `build_scientific_manifest` converts a `LabLoopRun` into the existing `ScientificRunManifest`. The adapter `evaluate_lab_loop_run` then uses the existing Scientific Agent Gates without creating a parallel governance path.

## 3. Subagent review board

The initial board is deliberately broad but narrow in responsibility:

| Role | Purpose |
| --- | --- |
| Research Scout | Collect source links, repo context, and constraints. |
| Hypothesis Architect | Convert intent into falsifiable hypotheses. |
| Protocol Planner | Define repeatable steps and replay commands. |
| Sandbox Executor | Run the smallest safe experiment. |
| Evidence Graph Curator | Attach claims to sources and traces. |
| Verification Critic | Challenge weak claims and missing evidence. |
| Safety Guardian | Block PHI leakage and unsafe autonomy claims. |
| Metrics Accountant | Record cost, latency, token, and outcome metrics. |
| Deployment Inspector | Check Vercel, Hugging Face, GitHub, and demos. |
| Paper Scribe | Draft methods, results, limitations, and next tests. |
| Distribution Editor | Prepare truthful release notes and model cards. |
| Red Team Auditor | Triple-check from science, product, security, deployment, and public-claim perspectives. |

## 4. Connector diagnostics

The first pass tested connector availability rather than pretending to complete an unobserved wet-lab experiment.

| Connector | Result | Interpretation |
| --- | --- | --- |
| GitHub | pass | Repository metadata, branch creation, file fetch, and file creation worked. |
| Linear | pass | Raven AI Production Line exists with roadmap milestones. |
| Vercel | warn | Project listing and runtime error checks worked; no deployments or Agent Run traces were found for checked Raven projects. |
| Replit | blocked | App listing worked, but two app-agent inspections returned `phase: paused` with no response. |
| Hugging Face | read-only | Raven and OpenClinical repo details were readable, but no write/update action was exposed. |
| X | blocked | The X URL did not expose readable text through browser fetch. |
| Capable | pass | The public careers page was readable and provides the closed-loop conceptual inspiration. |
| MCP Registry | pass | Registry query worked and returned Replit-related MCP entries, including a Replit SSH server with timeout configuration. |

## 5. Tests

The initial test suite verifies four behaviors:

1. the default subagent board covers the full scientific loop;
2. connector receipts become scientific evidence sources;
3. a complete lab-loop run passes the Scientific Agent Gates;
4. missing receipts block publishable claims.

The replay command is:

```bash
pytest -q tests/test_lab_loop.py tests/test_scientific_agent_gates.py
```

## 6. Results

The implementation creates a software-side lab-loop record that can be compiled into an existing Raven scientific gate manifest. The design is intentionally conservative: Replit paused execution is represented as a blocked receipt; Vercel missing deployments are represented as warnings; Hugging Face read-only access is represented as read-only evidence; and X unreadability is represented as blocked source extraction.

The strongest supported result is architectural: Raven can now encode multi-agent scientific work as structured, testable, evidence-gated records.

## 7. Limitations

No wet-lab data were generated. No therapeutic molecule, protein, RNA, DNA, binder, or clinical intervention was designed or validated. Replit did not provide runnable app-agent inspection output during this pass. Vercel did not show Agent Run traces. Hugging Face write/publish actions were not available through the exposed connector. Therefore, this paper is a software systems report, not a biological or clinical validation paper.

## 8. Next work

1. Resume the Replit app-agent sessions and capture runnable demo receipts.
2. Add Vercel deployments or preview URLs for the Raven public demo.
3. Publish a Hugging Face model-card update through an available write path, manual UI, or a future connector that exposes write operations.
4. Add benchmark fixtures for Evidence Graph scoring, Token Economy savings, and gate false-positive/false-negative behavior.
5. Create a release packet that links GitHub PR, Linear issue, Vercel preview, Replit demo, Hugging Face card, and public claim wording.

## 9. Public claim policy

Approved wording: Raven includes an auditable software contract for representing agentic lab-loop records across connectors.

Blocked wording: Raven autonomously discovers therapeutics, validates clinical interventions, or performs same-day synthesis-to-testing cycles.

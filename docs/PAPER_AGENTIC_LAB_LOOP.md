# Raven Agentic Lab Loop: A Reproducible Software Analogue for Closed-Loop AI R&D

## Abstract

Capable's public thesis emphasizes collapsing the loop between research, synthesis, and testing. Raven AI adopts the same systems principle in a software-safe form: every research claim must pass through hypothesis capture, connector-backed sandbox inspection, Evidence Graph tracing, Token Economy planning, Scientific Agent Gates, and restrained publication. This paper describes the implementation of `runtime/agentic_lab_loop.py`, the connector receipts collected during this session, and the tests added in `tests/test_agentic_lab_loop.py`.

This is not a wet-lab automation claim, a clinical validation claim, or a medical-device claim. It is a reproducible software orchestration pattern for agentic research workflows.

## Research Question

Can Raven represent closed-loop software research with connector-backed receipts?

## Hypothesis

If every connector observation becomes evidence, then Raven can separate measured progress from unsupported claims.

## Method

We implemented a dependency-light lab-loop module with four core objects:

1. `LabLoopTask`, which records the question, hypothesis, risk tier, PHI flag, code artifacts, output artifacts, replay command, and environment fingerprint.
2. `ConnectorReceipt`, which records observations from GitHub, Replit, Vercel, Linear, Hugging Face, or manual/local execution.
3. `SubAgentSpec`, which decomposes review into narrow perspectives including hypothesis, literature, protocol, biosecurity, code, sandbox, CI, Vercel, Linear, Hugging Face, statistics, red team, paper writing, and release notarization.
4. `LabLoopResult`, which bundles the task, receipts, evidence trace, token plan, scientific manifest, and gate report.

The module imports Raven's existing `EvidenceGraph`, `TokenEconomyRequest`, `plan_token_economy`, `ScientificRunManifest`, `manifest_from_evidence_trace`, and `evaluate_scientific_run`. Connector observations become Evidence Graph sources and claims. The manifest is then evaluated by Scientific Agent Gates before public claims are allowed.

## Connector Test Receipts

The following connector receipts were encoded in tests and documentation:

| Connector | Target | Result | Interpretation |
| --- | --- | --- | --- |
| GitHub | `simpliibarrii-crypto/raven-ai` | pass | Repository is accessible and accepted branch commits. |
| Vercel | `home-for-ai` | warn | Project exists, but no production deployments were listed during inspection. Runtime error scans returned no errors for checked project windows. |
| Replit | `home-for-ai` | paused | App exists, but Replit Agent inspection returned a paused response, so no Replit execution-success claim is made. |
| Linear | `Raven AI Production Line` | pass | Project exists with milestones for Evidence Graph, Token Economy, Scientific Gates, Vercel, Replit, and distribution. |
| Hugging Face | `bclermo/raven-ai` | warn | Model and Space metadata are visible; current connector supports inspection/jobs but not direct repo publishing in this session. |

## Results

The added tests verify that:

- Raven creates a `raven.agentic_lab_loop.v1` bundle.
- Raven emits a `raven.evidence_graph.v1` trace.
- The software lab-loop manifest passes Scientific Agent Gates when scoped to software evidence and non-PHI claims.
- At least twelve specialized subagent perspectives are attached.
- PHI-bearing runs are blocked from public publishing.
- Mixed connector receipt states are counted deterministically.

The tests are replayable with:

```bash
pytest -q tests/test_agentic_lab_loop.py
```

## Limitations

This paper reports connector-backed software inspection, not wet-lab synthesis, biological testing, clinical validation, patient outcome evidence, or production deployment certification. The Replit inspection returned a paused response rather than an execution transcript. Vercel showed project metadata and runtime-error checks, but no production deployments were listed for the inspected `home-for-ai` projects. Hugging Face metadata was inspectable, but direct publishing to Hugging Face was not available through the exposed connector actions in this session.

## Safety and Governance

Raven's lab loop explicitly prevents public claims when PHI is present. It also prevents state-of-the-art claims without held-out evaluation through the existing Scientific Agent Gates. Clinical, therapeutic, or autonomous-discovery language must remain scoped until independent validation exists.

## Conclusion

Raven now has the software skeleton of a Capable-style closed loop: hypothesis, subagents, receipts, evidence, cost-aware planning, gates, paper, and release packet. The next valid milestone is to run the tests in CI, attach the workflow receipt, connect the Vercel project to an actual deployed demo, and replace the paused Replit receipt with a successful execution transcript.

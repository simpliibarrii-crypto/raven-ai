# Scientific Agent Gates

Raven should not treat scientific agents as magic notebooks. A scientific run is only useful when it is evidence-linked, replayable, cost-aware, privacy-aware, and honest about uncertainty.

This document maps recent AI research into Raven implementation rules.

## Research Signals

| Paper / signal | Raven lesson | Implementation |
|---|---|---|
| DSpark: Confidence-Scheduled Speculative Decoding with Semi-Autoregressive Generation | Do cheap drafting first, then verify adaptively by confidence and load. | Raven Token Economy and gate checks for complete token-economy metadata. |
| Explainable Biomedical Claim Verification with Large Language Models | Scientific and clinical claims need explicit support, contradiction, or insufficient-evidence labels. | `ScientificClaimCheck` with `support`, `contradict`, and `not_enough_information`. |
| ScienceAgentBench | Scientific agents should be evaluated on executable, isolated tasks before end-to-end automation claims. | Reproducibility gates require code artifacts, output artifacts, metrics, replay command, and environment fingerprint. |
| PaperBench | Research replication should decompose work into small, gradable subtasks instead of vague “replicated paper” claims. | Raven gates block public claims without traceable artifacts and metrics. |
| AI Agents That Matter | Accuracy alone is not enough; agents must optimize accuracy, cost, reproducibility, and overfitting resistance together. | Gate scoring includes evidence, token/cost metadata, and held-out evaluation flags. |
| AlphaEvolve / DeepEvolve-style loops | Scientific improvement loops need objective evaluators, executable candidates, and measured gains. | State-of-the-art claims require held-out evaluation before publishing. |

## Runtime API

The dependency-free implementation lives in `runtime/scientific_agent_gates.py`.

```python
from runtime.scientific_agent_gates import (
    ScientificClaimCheck,
    ScientificRunManifest,
    evaluate_scientific_run,
)

manifest = ScientificRunManifest(
    run_id="run-001",
    task_id="bio-task-001",
    question="Which source supports the workflow claim?",
    hypothesis="Evidence-linked workflows should be easier to audit.",
    workflow_stage="analysis",
    sources=({"id": "source:paper", "title": "Validation paper", "kind": "paper"},),
    claim_checks=(
        ScientificClaimCheck(
            claim_id="claim:1",
            claim="Evidence-linked workflows preserve audit context.",
            evidence_label="support",
            source_ids=("source:paper",),
            confidence=0.84,
        ),
    ),
    code_artifacts=("scripts/replay.py",),
    output_artifacts=("artifacts/result.json",),
    metrics={"accuracy": 0.82, "cost_tokens": 1200},
    token_economy={
        "draft_lane": "local-small",
        "context_budget": 16000,
        "estimated_saved_context_tokens": 4000,
        "confidence_floor": 0.68,
        "verification_spans": ["uncertain claims only"],
    },
    evidence_trace={"schema": "raven.evidence_graph.v1"},
    replay_command="python scripts/replay.py",
    environment_fingerprint="python=3.11;pytest=8",
    human_reviewed=True,
)

report = evaluate_scientific_run(manifest)
assert report.can_publish is True
```

## Gate Rules

### Evidence gate

Every claim should have a claim-level evidence decision:

- `support`: evidence supports the claim.
- `contradict`: evidence contradicts the claim and blocks publishability.
- `not_enough_information`: evidence is insufficient and warns the reviewer.

### Reproducibility gate

Executable scientific stages require:

- code artifacts,
- output artifacts,
- metrics,
- a replay command,
- an environment fingerprint.

This follows the ScienceAgentBench and PaperBench lesson: do not claim scientific automation when the run cannot be replayed or graded.

### Token Economy gate

Every expensive run should explain token spend with:

- draft lane,
- context budget,
- estimated saved context tokens,
- confidence floor,
- verification spans.

This keeps DSpark-inspired token saving model-agnostic and honest.

### Privacy gate

PHI-bearing or private clinical work cannot route through remote lanes by default. If `contains_phi=True` and `draft_lane` starts with `remote`, the gate fails.

### Public-claim gate

Raven blocks state-of-the-art claims without held-out evaluation and blocks autonomous-discovery language without human review.

## Ecosystem Fit

| App | How it should use the gate |
|---|---|
| Raven AI | Source of truth for gate rules, claim checks, and run manifests. |
| Home for AI | Generate local run manifests before exporting or sharing run records. |
| OpenClinical AI | Use consent-gated manifests and never publish PHI-bearing traces. |
| Hermes Edge | Attach benchmark artifacts, route decisions, and device fingerprints before speed or cost claims. |

## What This Prevents

- unsupported biomedical claims,
- fake benchmark claims,
- unverifiable “agent did science” demos,
- token-saving claims without cost metadata,
- PHI accidentally routed through remote models,
- public state-of-the-art claims without held-out evaluation.

This makes Raven less flashy in the cheap way and more dangerous in the useful way: a quiet machine that can prove what it did.

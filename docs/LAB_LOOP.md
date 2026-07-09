# Raven Agentic Lab Loop

Raven Agentic Lab Loop is the closed-loop research pattern for Raven AI: capture a hypothesis, assign narrow subagents, run a safe sandbox experiment, convert connector receipts into evidence sources, gate the result, and only then prepare a paper, demo, release note, or model card.

This is inspired by the public direction of closed-loop AI science systems: rapid in-house data generation, ever-improving models, and collapsed research-to-testing cycles. Raven implements the software governance layer for that idea. It does not provide wet-lab instructions, synthesis protocols, clinical validation, or autonomous therapeutic claims.

## Loop contract

1. **Intake**: capture the user request, source URLs, repo targets, privacy scope, and allowed tools.
2. **Hypothesis**: turn the request into a falsifiable claim with measurable success criteria.
3. **Planning**: select subagents, tools, replay commands, and expected artifacts.
4. **Execution**: run the smallest safe experiment in GitHub CI, Replit, Vercel, Hugging Face, or a local sandbox.
5. **Evidence**: convert connector outputs into `ConnectorReceipt` records and Raven Evidence Graph sources.
6. **Verification**: check claim labels, confidence, source coverage, metrics, and contradictions.
7. **Safety**: block PHI leakage, unsafe biology claims, unsupported state-of-the-art language, and autonomous-discovery claims without human review.
8. **Metrics**: record test count, latency, token budget, cost estimate, connector coverage, and deployment health.
9. **Paper**: generate a restrained scientific report with methods, results, limitations, and replay instructions.
10. **Deployment**: only publish to public surfaces after gates pass or warnings are clearly disclosed.
11. **Distribution**: prepare release notes, README changes, Hugging Face model cards, and community updates.
12. **Red team**: review from product, science, security, clinical, deployment, and public-claim perspectives.

## Runtime API

```python
from runtime.lab_loop import ConnectorReceipt, LabLoopRun, default_subagents, evaluate_lab_loop_run

run = LabLoopRun(
    run_id="lab-loop-001",
    task_id="raven-lab-loop",
    question="Can connector receipts support publishable scientific claims?",
    hypothesis="Connector receipts improve reproducibility review.",
    workflow_stage="analysis",
    subagents=default_subagents(),
    connector_receipts=(
        ConnectorReceipt(surface="GitHub", status="pass", summary="Code and tests committed."),
        ConnectorReceipt(surface="Vercel", status="warn", summary="No runtime errors, no deployment receipt."),
    ),
    claims=("Raven can represent connector receipts as evidence sources.",),
    metrics={"connector_receipts": 2, "subagents": 12},
    token_economy={
        "draft_lane": "tool",
        "context_budget": 16000,
        "estimated_saved_context_tokens": 2400,
        "confidence_floor": 0.68,
        "verification_spans": ["connector receipts", "claim wording"],
    },
    evidence_trace={"schema": "raven.evidence_graph.v1"},
    code_artifacts=("runtime/lab_loop.py",),
    output_artifacts=("papers/raven_agentic_lab_loop.md",),
    replay_command="pytest -q tests/test_lab_loop.py tests/test_scientific_agent_gates.py",
    environment_fingerprint="python=3.11;pytest=8",
    human_reviewed=True,
)

report = evaluate_lab_loop_run(run)
print(report.status, report.can_publish)
```

## Connector status model

Each connector is treated as an evidence source, not as magical authority.

| Status | Meaning | Public claim behavior |
| --- | --- | --- |
| `pass` | Tool returned useful evidence or completed the requested action. | Can support claims if linked to metrics and artifacts. |
| `warn` | Tool returned partial evidence, empty deployment data, or non-blocking uncertainty. | Must be disclosed in report limitations. |
| `fail` | Tool returned an error that invalidates the claim. | Blocks publishable claims unless fixed. |
| `blocked` | Permission, safety, or policy stopped the action. | Blocks action and requires explicit resolution. |
| `not_run` | The connector was not tested. | Cannot support claims. |

## Current repo targets

- `raven-ai`: core Evidence Graph, Token Economy, Scientific Gates, and Lab Loop contract.
- `openclinical-ai`: clinical/healthcare runtime surface that must stay PHI-aware and non-diagnostic unless formally validated.
- `home-for-ai`: desktop orchestration surface for local command and connector control.

## Replay

```bash
pytest -q tests/test_lab_loop.py tests/test_scientific_agent_gates.py
```

## Release rule

A Raven Lab Loop output is publishable only when:

- there is a stable task id, research question, and hypothesis;
- sources and claim checks exist;
- executable workflows include code artifacts, output artifacts, metrics, replay command, and environment fingerprint;
- PHI is not routed to remote lanes or public artifacts;
- state-of-the-art and autonomous-discovery claims have held-out evaluation and human review;
- public copy describes limitations honestly.

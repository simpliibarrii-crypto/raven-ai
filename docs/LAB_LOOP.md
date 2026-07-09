# Raven Agentic Lab Loop

Raven Agentic Lab Loop is the closed-loop research pattern for Raven AI: capture a hypothesis, assign narrow subagents, run or inspect safe sandboxes, convert connector receipts into evidence sources, gate the result, and only then prepare a paper, demo, release note, or model card.

This is inspired by closed-loop AI science systems: rapid data generation, ever-improving models, and collapsed research-to-testing cycles. Raven implements the software governance layer for that idea. It does not provide wet-lab instructions, synthesis protocols, clinical validation, or autonomous therapeutic claims.

## Loop contract

1. **Hypothesis**: turn intent into a falsifiable question with measurable success criteria.
2. **Planning**: select subagents, tools, replay commands, and expected artifacts.
3. **Execution**: run or inspect the smallest safe experiment in GitHub CI, Replit, Vercel, Hugging Face, or a local sandbox.
4. **Evidence**: convert connector outputs into `ConnectorReceipt` records and Raven Evidence Graph sources.
5. **Verification**: check claim labels, confidence, source coverage, metrics, and contradictions.
6. **Safety**: block PHI leakage, unsafe biology claims, unsupported state-of-the-art language, and autonomous-discovery claims without human review.
7. **Metrics**: record test count, latency, token budget, cost estimate, connector coverage, and deployment health.
8. **Paper**: generate a restrained scientific report with methods, results, limitations, and replay instructions.
9. **Deployment**: only publish to public surfaces after gates pass or warnings are clearly disclosed.
10. **Distribution**: prepare release notes, README changes, Hugging Face model cards, and community updates.
11. **Red team**: review from product, science, security, clinical, deployment, and public-claim perspectives.

## Runtime API

```python
from runtime.agentic_lab_loop import ConnectorReceipt, LabLoopTask, plan_lab_loop

receipts = (
    ConnectorReceipt(
        connector="github",
        target="simpliibarrii-crypto/raven-ai",
        observation="Repository is accessible and branch commits are available.",
        status="pass",
    ),
    ConnectorReceipt(
        connector="replit",
        target="home-for-ai",
        observation="App exists, but agent inspection returned a paused response.",
        status="paused",
    ),
)

task = LabLoopTask(
    task_id="raven-lab-loop",
    question="Can connector receipts support publishable software-science claims?",
    hypothesis="Connector receipts improve reproducibility review.",
)

result = plan_lab_loop(task, receipts)
print(result.gate_report.status, result.gate_report.can_publish)
```

## Connector status model

Each connector is treated as an evidence source, not as magical authority.

| Status | Meaning | Public claim behavior |
| --- | --- | --- |
| `pass` | Tool returned useful evidence or completed the requested action. | Can support claims if linked to metrics and artifacts. |
| `warn` | Tool returned partial evidence, empty deployment data, or non-blocking uncertainty. | Must be disclosed in report limitations. |
| `fail` | Tool returned an error that invalidates the claim. | Blocks publishable claims unless fixed. |
| `paused` | The connector reached an app/session but the agent did not complete. | Blocks execution-success claims until resumed. |
| `not_available` | The connector action is not exposed in this session. | Cannot support publish/publish-like claims. |

## Current repo targets

- `raven-ai`: core Evidence Graph, Token Economy, Scientific Gates, and Agentic Lab Loop contract.
- `openclinical-ai`: clinical/healthcare runtime surface that must stay PHI-aware and non-diagnostic unless formally validated.
- `home-for-ai`: desktop orchestration surface for local command and connector control.

## Replay

```bash
pytest -q tests/test_agentic_lab_loop.py tests/test_scientific_agent_gates.py
```

## Release rule

A Raven Agentic Lab Loop output is publishable only when:

- there is a stable task id, research question, and hypothesis;
- sources and claim checks exist;
- executable workflows include code artifacts, output artifacts, metrics, replay command, and environment fingerprint;
- PHI is not routed to remote lanes or public artifacts;
- state-of-the-art and autonomous-discovery claims have held-out evaluation and human review;
- public copy describes limitations honestly.

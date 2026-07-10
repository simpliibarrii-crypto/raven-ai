from __future__ import annotations

from runtime.agentic_lab_loop import ConnectorReceipt, LabLoopTask, aggregate_receipt_metrics, plan_lab_loop


def sample_receipts() -> tuple[ConnectorReceipt, ...]:
    return (
        ConnectorReceipt(
            connector="github",
            target="simpliibarrii-crypto/raven-ai",
            observation="Repository is accessible and the agentic-lab-loop branch can receive commits.",
            status="pass",
            metrics={"repos_checked": 1},
        ),
        ConnectorReceipt(
            connector="vercel",
            target="home-for-ai",
            observation="Project exists. No production deployments were listed during connector inspection.",
            status="warn",
            metrics={"deployments_found": 0},
        ),
        ConnectorReceipt(
            connector="replit",
            target="home-for-ai",
            observation="App exists, but Replit Agent inspection returned a paused response.",
            status="paused",
            metrics={"apps_found": 1},
        ),
        ConnectorReceipt(
            connector="linear",
            target="Raven AI Production Line",
            observation="Project exists with milestones for Evidence Graph, Token Economy, Scientific Gates, Vercel, Replit, and distribution.",
            status="pass",
            metrics={"projects_found": 2},
        ),
        ConnectorReceipt(
            connector="huggingface",
            target="bclermo/raven-ai",
            observation="Model and Space metadata are visible; connector supports inspection but not repository publishing in this session.",
            status="warn",
            metrics={"repos_checked": 2},
        ),
    )


def test_plan_lab_loop_builds_publishable_software_manifest():
    task = LabLoopTask(
        task_id="capable-style-closed-loop-software-rd",
        question="Can Raven represent closed-loop software research with connector-backed receipts?",
        hypothesis="If every connector observation becomes evidence, then Raven can separate measured progress from unsupported claims.",
        risk="medium",
    )

    result = plan_lab_loop(task, sample_receipts())

    assert result.to_dict()["schema"] == "raven.agentic_lab_loop.v1"
    assert result.evidence_trace["schema"] == "raven.evidence_graph.v1"
    assert result.gate_report.status == "pass"
    assert result.gate_report.can_publish is True
    assert len(result.subagents) >= 12
    assert result.manifest.replay_command == "pytest -q tests/test_agentic_lab_loop.py"


def test_phi_never_publishes_publicly():
    task = LabLoopTask(
        task_id="phi-guard",
        question="Can a PHI-bearing run publish publicly?",
        hypothesis="PHI-bearing runs should be blocked from public publishing.",
        risk="high",
        contains_phi=True,
    )

    result = plan_lab_loop(task, sample_receipts())

    assert result.gate_report.can_publish is False
    assert any(finding.code == "phi-private-output" for finding in result.gate_report.findings)


def test_aggregate_receipt_metrics_counts_connector_states():
    metrics = aggregate_receipt_metrics(sample_receipts())

    assert metrics["connector_receipts"] == 5
    assert metrics["passing_receipts"] == 2
    assert metrics["warning_receipts"] == 2
    assert metrics["paused_receipts"] == 1
    assert metrics["receipt_pass_rate"] == 0.4

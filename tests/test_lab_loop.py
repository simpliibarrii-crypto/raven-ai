from __future__ import annotations

from runtime.lab_loop import (
    ConnectorReceipt,
    LabLoopRun,
    build_scientific_manifest,
    default_subagents,
    evaluate_lab_loop_run,
    subagents_by_role,
)


def _token_economy() -> dict[str, object]:
    return {
        "draft_lane": "tool",
        "context_budget": 16000,
        "estimated_saved_context_tokens": 2400,
        "confidence_floor": 0.68,
        "verification_spans": ["connector receipts", "deployment evidence", "claim wording"],
    }


def _good_run() -> LabLoopRun:
    return LabLoopRun(
        run_id="lab-loop-001",
        task_id="raven-lab-loop",
        question="Can Raven convert agent work into publishable scientific run records?",
        hypothesis="A connector-receipt lab loop improves auditability before public publication.",
        workflow_stage="analysis",
        subagents=default_subagents(),
        connector_receipts=(
            ConnectorReceipt(
                surface="GitHub",
                status="pass",
                summary="Repository, branch, code, and paper artifacts were created for review.",
                evidence=("runtime/lab_loop.py", "tests/test_lab_loop.py"),
            ),
            ConnectorReceipt(
                surface="Linear",
                status="pass",
                summary="Execution work can be tracked through the Raven AI Production Line project.",
                evidence=("Raven AI Production Line",),
            ),
            ConnectorReceipt(
                surface="Vercel",
                status="warn",
                summary="Runtime error checks returned no recent errors, but no deployment receipt was present.",
                evidence=("home-for-ai", "home-for-ai-ui"),
            ),
        ),
        claims=(
            "Raven can represent connector receipts as publishable evidence sources.",
            "Raven can gate scientific outputs before public release.",
        ),
        metrics={"connector_receipts": 3, "subagents": 12, "blocking_failures": 0},
        token_economy=_token_economy(),
        evidence_trace={"schema": "raven.evidence_graph.v1"},
        code_artifacts=("runtime/lab_loop.py", "tests/test_lab_loop.py"),
        output_artifacts=("papers/raven_agentic_lab_loop.md",),
        replay_command="pytest -q tests/test_lab_loop.py tests/test_scientific_agent_gates.py",
        environment_fingerprint="python=3.11;pytest=8;github-actions=ubuntu-latest",
        human_reviewed=True,
    )


def test_default_subagents_cover_full_scientific_loop():
    roles = {agent.role for agent in default_subagents()}

    assert len(default_subagents()) >= 12
    assert {
        "intake",
        "hypothesis",
        "planning",
        "execution",
        "evidence",
        "verification",
        "safety",
        "metrics",
        "deployment",
        "paper",
        "distribution",
        "red_team",
    }.issubset(roles)
    assert subagents_by_role("red_team")[0].name == "Red Team Auditor"


def test_connector_receipts_become_scientific_sources():
    manifest = build_scientific_manifest(_good_run())

    assert len(manifest.sources) == 3
    assert {source["id"] for source in manifest.sources} == {
        "connector:github",
        "connector:linear",
        "connector:vercel",
    }
    assert all(check.evidence_label == "support" for check in manifest.claim_checks)


def test_good_lab_loop_passes_scientific_gates():
    report = evaluate_lab_loop_run(_good_run())

    assert report.status == "pass"
    assert report.can_publish is True
    assert report.can_autorun is True
    assert report.required_actions == ()


def test_missing_receipts_block_publishable_claims():
    run = LabLoopRun(
        run_id="lab-loop-empty",
        task_id="raven-lab-loop",
        question="Can claims be published without receipts?",
        hypothesis="Missing receipts should fail publish gates.",
        workflow_stage="analysis",
        claims=("This claim has no connector receipt.",),
        metrics={"connector_receipts": 0},
        token_economy=_token_economy(),
        evidence_trace={"schema": "raven.evidence_graph.v1"},
        code_artifacts=("runtime/lab_loop.py",),
        output_artifacts=("papers/raven_agentic_lab_loop.md",),
        replay_command="pytest -q tests/test_lab_loop.py",
        environment_fingerprint="python=3.11;pytest=8",
        human_reviewed=True,
    )

    report = evaluate_lab_loop_run(run)

    assert report.status == "fail"
    assert report.can_publish is False
    assert any(finding.code == "missing-sources" for finding in report.findings)

from __future__ import annotations

from runtime.scientific_agent_gates import (
    ScientificClaimCheck,
    ScientificRunManifest,
    evaluate_scientific_run,
    manifest_from_evidence_trace,
)


def good_manifest() -> ScientificRunManifest:
    return ScientificRunManifest(
        run_id="run-001",
        task_id="bio-task-001",
        question="Which source supports the workflow claim?",
        hypothesis="Evidence-linked workflows should be easier to audit.",
        workflow_stage="analysis",
        risk="medium",
        sources=(
            {"id": "source:paper", "title": "Validation paper", "kind": "paper"},
        ),
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


def test_good_manifest_passes_and_can_publish():
    report = evaluate_scientific_run(good_manifest())

    assert report.status == "pass"
    assert report.can_publish is True
    assert report.can_autorun is True
    assert report.required_actions == ()


def test_contradicted_claim_blocks_publish():
    manifest = good_manifest()
    bad = ScientificRunManifest(
        **{
            **manifest.__dict__,
            "claim_checks": (
                ScientificClaimCheck(
                    claim_id="claim:bad",
                    claim="The workflow is clinically validated.",
                    evidence_label="contradict",
                    source_ids=("source:paper",),
                    confidence=0.91,
                ),
            ),
        }
    )

    report = evaluate_scientific_run(bad)

    assert report.status == "fail"
    assert report.can_publish is False
    assert "Remove, revise, or explicitly mark the answer as contradicted." in report.required_actions


def test_state_of_art_claim_requires_heldout_eval():
    manifest = good_manifest()
    soa = ScientificRunManifest(
        **{
            **manifest.__dict__,
            "claims_state_of_art": True,
            "heldout_eval": False,
        }
    )

    report = evaluate_scientific_run(soa)

    assert report.status == "fail"
    assert any(finding.code == "state-of-art-without-heldout" for finding in report.findings)


def test_phi_on_remote_lane_fails_and_cannot_publish():
    manifest = good_manifest()
    phi = ScientificRunManifest(
        **{
            **manifest.__dict__,
            "contains_phi": True,
            "token_economy": {
                **manifest.token_economy,
                "draft_lane": "remote-cheap",
            },
        }
    )

    report = evaluate_scientific_run(phi)

    assert report.status == "fail"
    assert report.can_publish is False
    assert any(finding.code == "phi-remote-lane" for finding in report.findings)


def test_manifest_from_evidence_trace_imports_claims_and_sources():
    trace = {
        "schema": "raven.evidence_graph.v1",
        "confidence": 0.77,
        "sources": [{"id": "source:a", "title": "A"}],
        "claims": [
            {"id": "claim:a", "text": "A claim with a source.", "source_ids": ["source:a"]},
            {"id": "claim:b", "text": "A claim without enough evidence.", "source_ids": []},
        ],
    }

    manifest = manifest_from_evidence_trace(
        run_id="run-trace",
        task_id="trace-task",
        question="What happened?",
        hypothesis="Trace import should preserve claim decisions.",
        workflow_stage="literature_review",
        evidence_trace=trace,
    )
    report = evaluate_scientific_run(manifest)

    assert len(manifest.claim_checks) == 2
    assert manifest.claim_checks[0].evidence_label == "support"
    assert manifest.claim_checks[1].evidence_label == "not_enough_information"
    assert report.status == "warn"

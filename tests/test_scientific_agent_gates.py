from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

from runtime.scientific_agent_gates import (
    AtomicFactEvaluation,
    ScientificBenchmarkManifest,
    ScientificClaimCheck,
    ScientificEvaluationStep,
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


def passing_benchmark() -> ScientificBenchmarkManifest:
    return ScientificBenchmarkManifest(
        benchmark_id="literature-synthesis-v1",
        steps=(
            ScientificEvaluationStep(
                step_id="retrieve",
                description="Retrieve only papers from the declared source set.",
                expected_artifact="artifacts/retrieval_manifest.json",
                pass_criterion="Every accessed source id appears in the allowlist.",
                status="pass",
                observed_artifact="artifacts/retrieval_manifest.json",
            ),
            ScientificEvaluationStep(
                step_id="verify",
                description="Verify each synthesized atomic fact against a source.",
                expected_artifact="artifacts/atomic_facts.json",
                pass_criterion="No unsupported or contradictory facts remain.",
                status="pass",
                observed_artifact="artifacts/atomic_facts.json",
            ),
        ),
        atomic_facts=AtomicFactEvaluation(
            supported_count=4,
            unsupported_count=0,
            contradictory_count=0,
            reference_count=4,
        ),
        clean_room=True,
        allowed_source_ids=("source:paper",),
        precision_floor=1.0,
        recall_floor=1.0,
    )


def test_good_manifest_passes_and_can_publish():
    report = evaluate_scientific_run(good_manifest())

    assert report.status == "pass"
    assert report.can_publish is True
    assert report.can_autorun is True
    assert report.required_actions == ()


def test_contradicted_claim_blocks_publish():
    manifest = good_manifest()
    bad = replace(
        manifest,
        claim_checks=(
            ScientificClaimCheck(
                claim_id="claim:bad",
                claim="The workflow is clinically validated.",
                evidence_label="contradict",
                source_ids=("source:paper",),
                confidence=0.91,
            ),
        ),
    )

    report = evaluate_scientific_run(bad)

    assert report.status == "fail"
    assert report.can_publish is False
    assert (
        "Remove, revise, or explicitly mark the answer as contradicted."
        in report.required_actions
    )


def test_state_of_art_claim_requires_heldout_eval():
    report = evaluate_scientific_run(
        replace(good_manifest(), claims_state_of_art=True, heldout_eval=False)
    )

    assert report.status == "fail"
    assert any(
        finding.code == "state-of-art-without-heldout" for finding in report.findings
    )


def test_phi_on_remote_lane_fails_and_cannot_publish():
    manifest = good_manifest()
    phi = replace(
        manifest,
        contains_phi=True,
        token_economy={
            **manifest.token_economy,
            "draft_lane": "remote-cheap",
        },
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


def test_stepwise_benchmark_passes_clean_room_publishability_gate():
    report = evaluate_scientific_run(
        replace(good_manifest(), benchmark=passing_benchmark())
    )

    assert report.status == "pass"
    assert report.can_publish is True
    assert not any(finding.code.startswith("benchmark-") for finding in report.findings)


def test_partial_benchmark_warns_when_pending_steps_are_allowed():
    benchmark = replace(
        passing_benchmark(),
        require_all_steps=False,
        steps=(
            passing_benchmark().steps[0],
            replace(
                passing_benchmark().steps[1],
                status="pending",
                observed_artifact=None,
            ),
        ),
    )
    report = evaluate_scientific_run(replace(good_manifest(), benchmark=benchmark))

    assert report.status == "warn"
    assert report.can_publish is True
    assert any(finding.code == "benchmark-step-pending" for finding in report.findings)


def test_contradictory_atomic_fact_blocks_publishability():
    benchmark = replace(
        passing_benchmark(),
        atomic_facts=AtomicFactEvaluation(
            supported_count=3,
            unsupported_count=0,
            contradictory_count=1,
            reference_count=4,
        ),
        precision_floor=0.7,
        recall_floor=0.7,
    )
    report = evaluate_scientific_run(replace(good_manifest(), benchmark=benchmark))

    assert report.status == "fail"
    assert report.can_publish is False
    assert any(
        finding.code == "contradictory-atomic-facts" for finding in report.findings
    )


def test_clean_room_source_leakage_blocks_publishability():
    benchmark = replace(
        passing_benchmark(),
        allowed_source_ids=("source:other",),
    )
    report = evaluate_scientific_run(replace(good_manifest(), benchmark=benchmark))

    assert report.status == "fail"
    assert report.can_publish is False
    assert any(
        finding.code == "clean-room-source-leakage" for finding in report.findings
    )


def test_benchmark_packet_and_example_fixture_are_json_serializable():
    packet = passing_benchmark().to_dict()
    encoded = json.dumps(packet, sort_keys=True)

    assert '"schema": "raven.scientific_benchmark.v1"' in encoded
    assert packet["atomic_facts"]["precision"] == 1.0
    assert packet["atomic_facts"]["recall"] == 1.0
    assert packet["allowed_source_ids"] == ["source:paper"]

    fixture_path = (
        Path(__file__).parents[1]
        / "examples"
        / "fixtures"
        / "literature_synthesis_benchmark.json"
    )
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))

    assert fixture["schema"] == "raven.scientific_benchmark.v1"
    assert fixture["clean_room"] is True
    assert fixture["atomic_facts"]["unsupported_count"] == 0
    assert fixture["atomic_facts"]["contradictory_count"] == 0

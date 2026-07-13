from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

EvidenceLabel = Literal["support", "contradict", "not_enough_information"]
FindingSeverity = Literal["info", "warn", "fail"]
RiskTier = Literal["low", "medium", "high", "critical"]
WorkflowStage = Literal["literature_review", "experimentation", "analysis", "report", "deployment"]
EvaluationStepStatus = Literal["pass", "fail", "pending"]

SEVERITY_WEIGHT: dict[FindingSeverity, float] = {"info": 0.0, "warn": 0.08, "fail": 0.22}
RISK_WEIGHT: dict[RiskTier, int] = {"low": 0, "medium": 1, "high": 2, "critical": 3}
BENCHMARK_SCHEMA = "raven.scientific_benchmark.v1"


@dataclass(frozen=True)
class ScientificClaimCheck:
    """Claim-level evidence decision inspired by biomedical claim-verification work."""

    claim_id: str
    claim: str
    evidence_label: EvidenceLabel
    source_ids: tuple[str, ...] = ()
    confidence: float = 0.5
    rationale: str = ""


@dataclass(frozen=True)
class ScientificEvaluationStep:
    """One independently verifiable step in a scientific-agent benchmark."""

    step_id: str
    description: str
    expected_artifact: str
    pass_criterion: str
    status: EvaluationStepStatus = "pending"
    observed_artifact: str | None = None
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "step_id": self.step_id,
            "description": self.description,
            "expected_artifact": self.expected_artifact,
            "pass_criterion": self.pass_criterion,
            "status": self.status,
            "observed_artifact": self.observed_artifact,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class AtomicFactEvaluation:
    """Atomic-fact counts and deterministic precision/recall calculations."""

    supported_count: int = 0
    unsupported_count: int = 0
    contradictory_count: int = 0
    reference_count: int = 0

    @property
    def predicted_count(self) -> int:
        return self.supported_count + self.unsupported_count + self.contradictory_count

    @property
    def precision(self) -> float:
        if self.predicted_count == 0:
            return 0.0
        return round(self.supported_count / self.predicted_count, 4)

    @property
    def recall(self) -> float:
        if self.reference_count == 0:
            return 0.0
        return round(self.supported_count / self.reference_count, 4)

    def to_dict(self) -> dict[str, int | float]:
        return {
            "supported_count": self.supported_count,
            "unsupported_count": self.unsupported_count,
            "contradictory_count": self.contradictory_count,
            "reference_count": self.reference_count,
            "predicted_count": self.predicted_count,
            "precision": self.precision,
            "recall": self.recall,
        }


@dataclass(frozen=True)
class ScientificBenchmarkManifest:
    """Clean-room, stepwise benchmark contract for scientific-agent outputs."""

    benchmark_id: str
    steps: tuple[ScientificEvaluationStep, ...] = ()
    atomic_facts: AtomicFactEvaluation = field(default_factory=AtomicFactEvaluation)
    clean_room: bool = False
    allowed_source_ids: tuple[str, ...] = ()
    precision_floor: float = 0.0
    recall_floor: float = 0.0
    require_all_steps: bool = True
    require_no_unsupported: bool = True
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable benchmark packet."""

        return {
            "schema": BENCHMARK_SCHEMA,
            "benchmark_id": self.benchmark_id,
            "steps": [step.to_dict() for step in self.steps],
            "atomic_facts": self.atomic_facts.to_dict(),
            "clean_room": self.clean_room,
            "allowed_source_ids": list(self.allowed_source_ids),
            "precision_floor": self.precision_floor,
            "recall_floor": self.recall_floor,
            "require_all_steps": self.require_all_steps,
            "require_no_unsupported": self.require_no_unsupported,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class ScientificRunManifest:
    """A replayable scientific-agent run record before public claims are made."""

    run_id: str
    task_id: str
    question: str
    hypothesis: str
    workflow_stage: WorkflowStage
    risk: RiskTier = "medium"
    sources: tuple[dict[str, Any], ...] = ()
    claim_checks: tuple[ScientificClaimCheck, ...] = ()
    code_artifacts: tuple[str, ...] = ()
    output_artifacts: tuple[str, ...] = ()
    metrics: dict[str, float | int | str] = field(default_factory=dict)
    token_economy: dict[str, Any] = field(default_factory=dict)
    evidence_trace: dict[str, Any] = field(default_factory=dict)
    replay_command: str | None = None
    environment_fingerprint: str | None = None
    heldout_eval: bool = False
    human_reviewed: bool = False
    contains_phi: bool = False
    claims_state_of_art: bool = False
    claims_autonomous_discovery: bool = False
    notes: str = ""
    benchmark: ScientificBenchmarkManifest | None = None


@dataclass(frozen=True)
class GateFinding:
    severity: FindingSeverity
    code: str
    message: str
    action: str


@dataclass(frozen=True)
class GateReport:
    run_id: str
    status: Literal["pass", "warn", "fail"]
    score: float
    can_publish: bool
    can_autorun: bool
    findings: tuple[GateFinding, ...]

    @property
    def required_actions(self) -> tuple[str, ...]:
        return tuple(finding.action for finding in self.findings if finding.severity == "fail")

    @property
    def warnings(self) -> tuple[str, ...]:
        return tuple(finding.message for finding in self.findings if finding.severity == "warn")


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def _finding(severity: FindingSeverity, code: str, message: str, action: str) -> GateFinding:
    return GateFinding(severity=severity, code=code, message=message, action=action)


def _source_ids(sources: tuple[dict[str, Any], ...]) -> set[str]:
    ids: set[str] = set()
    for source in sources:
        source_id = source.get("id")
        if isinstance(source_id, str) and source_id:
            ids.add(source_id)
    return ids


def _token_lane(token_economy: dict[str, Any]) -> str:
    lane = token_economy.get("draft_lane")
    return lane if isinstance(lane, str) else ""


def evaluate_scientific_run(manifest: ScientificRunManifest) -> GateReport:
    """Evaluate whether a scientific-agent run is publishable, replayable, and safe."""

    findings: list[GateFinding] = []
    known_sources = _source_ids(manifest.sources)

    if not manifest.task_id.strip():
        findings.append(_finding("fail", "missing-task-id", "The run has no stable task id.", "Assign a stable task id before review."))
    if not manifest.question.strip():
        findings.append(_finding("fail", "missing-question", "The run has no research question.", "Record the research question."))
    if not manifest.hypothesis.strip():
        findings.append(_finding("warn", "missing-hypothesis", "The run has no explicit hypothesis.", "Add a hypothesis or mark the workflow as exploratory."))

    if not manifest.sources:
        findings.append(_finding("fail", "missing-sources", "No evidence sources were attached.", "Attach source records before accepting claims."))
    if not manifest.evidence_trace:
        findings.append(_finding("fail", "missing-evidence-trace", "No Raven Evidence Graph trace was attached.", "Attach a raven.evidence_graph.v1 trace."))
    elif manifest.evidence_trace.get("schema") != "raven.evidence_graph.v1":
        findings.append(_finding("fail", "invalid-evidence-schema", "Evidence trace schema is missing or unsupported.", "Use raven.evidence_graph.v1."))

    if not manifest.claim_checks:
        findings.append(_finding("fail", "missing-claim-checks", "No claim-level verification decisions were recorded.", "Create claim checks with support, contradict, or not_enough_information labels."))
    else:
        findings.extend(_evaluate_claim_checks(manifest.claim_checks, known_sources))

    if manifest.workflow_stage in {"experimentation", "analysis", "deployment"}:
        if not manifest.code_artifacts:
            findings.append(_finding("fail", "missing-code-artifacts", "No code artifact was recorded for an executable scientific workflow.", "Attach the script, notebook, or package path used to generate results."))
        if not manifest.output_artifacts:
            findings.append(_finding("fail", "missing-output-artifacts", "No output artifact was recorded for an executable scientific workflow.", "Attach result files, tables, figures, or benchmark artifacts."))
        if not manifest.replay_command:
            findings.append(_finding("fail", "missing-replay-command", "The run cannot be replayed from the manifest.", "Add a replay command or reproducible workflow entrypoint."))
        if not manifest.environment_fingerprint:
            findings.append(_finding("warn", "missing-environment", "No environment fingerprint was recorded.", "Record package versions, container digest, or runtime fingerprint."))

    if manifest.benchmark is not None:
        findings.extend(_evaluate_benchmark(manifest, known_sources))

    findings.extend(_evaluate_metrics_and_cost(manifest))
    findings.extend(_evaluate_privacy_and_claims(manifest))

    penalty = sum(SEVERITY_WEIGHT[finding.severity] for finding in findings)
    score = round(clamp(1.0 - penalty), 2)
    has_fail = any(finding.severity == "fail" for finding in findings)
    has_warn = any(finding.severity == "warn" for finding in findings)
    status: Literal["pass", "warn", "fail"] = "fail" if has_fail else "warn" if has_warn else "pass"
    can_publish = not has_fail and not manifest.contains_phi
    can_autorun = status == "pass" and RISK_WEIGHT[manifest.risk] < RISK_WEIGHT["high"] and not manifest.claims_autonomous_discovery

    return GateReport(
        run_id=manifest.run_id,
        status=status,
        score=score,
        can_publish=can_publish,
        can_autorun=can_autorun,
        findings=tuple(findings),
    )


def _evaluate_claim_checks(
    claim_checks: tuple[ScientificClaimCheck, ...],
    known_sources: set[str],
) -> list[GateFinding]:
    findings: list[GateFinding] = []
    for check in claim_checks:
        if not check.claim.strip():
            findings.append(_finding("fail", "empty-claim", f"Claim {check.claim_id!r} has no text.", "Replace empty claims with reviewable statements."))
        if check.evidence_label == "support" and not check.source_ids:
            findings.append(_finding("fail", "unsupported-support", f"Claim {check.claim_id!r} is marked support without sources.", "Attach at least one supporting source id."))
        if check.evidence_label == "support" and check.confidence < 0.55:
            findings.append(_finding("warn", "low-confidence-support", f"Claim {check.claim_id!r} is supported with low confidence.", "Verify the claim manually or downgrade the label."))
        if check.evidence_label == "contradict":
            findings.append(_finding("fail", "contradicted-claim", f"Claim {check.claim_id!r} is contradicted by evidence.", "Remove, revise, or explicitly mark the answer as contradicted."))
        if check.evidence_label == "not_enough_information":
            findings.append(_finding("warn", "insufficient-evidence", f"Claim {check.claim_id!r} lacks enough evidence.", "Keep the claim out of final answers or request more sources."))
        missing = [source_id for source_id in check.source_ids if known_sources and source_id not in known_sources]
        if missing:
            findings.append(_finding("fail", "unknown-source-id", f"Claim {check.claim_id!r} references unknown source ids: {', '.join(missing)}.", "Attach every referenced source to the run manifest."))
    return findings


def _evaluate_benchmark(
    manifest: ScientificRunManifest,
    known_sources: set[str],
) -> list[GateFinding]:
    benchmark = manifest.benchmark
    if benchmark is None:
        return []

    findings: list[GateFinding] = []
    if not benchmark.benchmark_id.strip():
        findings.append(_finding("fail", "missing-benchmark-id", "The benchmark has no stable id.", "Assign a stable benchmark id."))
    if not benchmark.steps:
        findings.append(_finding("fail", "missing-benchmark-steps", "The benchmark has no verifiable steps.", "Decompose the task into artifact-backed evaluation steps."))

    seen_step_ids: set[str] = set()
    for step in benchmark.steps:
        if not step.step_id.strip():
            findings.append(_finding("fail", "missing-step-id", "A benchmark step has no stable id.", "Assign every benchmark step a unique id."))
        elif step.step_id in seen_step_ids:
            findings.append(_finding("fail", "duplicate-step-id", f"Benchmark step id {step.step_id!r} is duplicated.", "Use unique step ids."))
        seen_step_ids.add(step.step_id)

        if not step.description.strip() or not step.expected_artifact.strip() or not step.pass_criterion.strip():
            findings.append(_finding("fail", "incomplete-step-contract", f"Benchmark step {step.step_id!r} lacks a description, expected artifact, or pass criterion.", "Complete the step contract before running the benchmark."))
        if step.status == "fail":
            findings.append(_finding("fail", "benchmark-step-failed", f"Benchmark step {step.step_id!r} failed its pass criterion.", "Fix or rerun the failed step before publication."))
        elif step.status == "pending":
            severity: FindingSeverity = "fail" if benchmark.require_all_steps else "warn"
            findings.append(_finding(severity, "benchmark-step-pending", f"Benchmark step {step.step_id!r} has not been evaluated.", "Evaluate the pending step and attach its observed artifact."))
        elif not step.observed_artifact:
            findings.append(_finding("fail", "missing-observed-artifact", f"Benchmark step {step.step_id!r} passed without an observed artifact.", "Attach the artifact that demonstrates the step passed."))

    fact_counts = (
        benchmark.atomic_facts.supported_count,
        benchmark.atomic_facts.unsupported_count,
        benchmark.atomic_facts.contradictory_count,
        benchmark.atomic_facts.reference_count,
    )
    if any(count < 0 for count in fact_counts):
        findings.append(_finding("fail", "invalid-atomic-fact-count", "Atomic-fact counts cannot be negative.", "Replace negative atomic-fact counts with valid non-negative values."))
    elif benchmark.atomic_facts.supported_count > benchmark.atomic_facts.reference_count:
        findings.append(_finding("fail", "invalid-atomic-fact-reference", "Supported atomic facts exceed the reference fact count.", "Correct the reference set or supported-fact count."))
    else:
        if benchmark.atomic_facts.contradictory_count > 0:
            findings.append(_finding("fail", "contradictory-atomic-facts", f"The synthesis contains {benchmark.atomic_facts.contradictory_count} contradictory atomic fact(s).", "Remove or explicitly resolve contradictory facts before publication."))
        if benchmark.require_no_unsupported and benchmark.atomic_facts.unsupported_count > 0:
            findings.append(_finding("fail", "unsupported-atomic-facts", f"The synthesis contains {benchmark.atomic_facts.unsupported_count} unsupported atomic fact(s).", "Remove unsupported facts or attach supporting evidence."))
        if benchmark.atomic_facts.precision < benchmark.precision_floor:
            findings.append(_finding("fail", "atomic-fact-precision-below-floor", f"Atomic-fact precision {benchmark.atomic_facts.precision:.4f} is below the required floor {benchmark.precision_floor:.4f}.", "Improve factual precision or lower the threshold with documented justification."))
        if benchmark.atomic_facts.recall < benchmark.recall_floor:
            findings.append(_finding("fail", "atomic-fact-recall-below-floor", f"Atomic-fact recall {benchmark.atomic_facts.recall:.4f} is below the required floor {benchmark.recall_floor:.4f}.", "Recover missing reference facts or lower the threshold with documented justification."))

    if benchmark.clean_room:
        allowed_sources = set(benchmark.allowed_source_ids)
        if not allowed_sources:
            findings.append(_finding("fail", "missing-clean-room-allowlist", "Clean-room evaluation has no allowed-source manifest.", "Declare the allowed source ids before evaluation."))
        unidentified_sources = [source for source in manifest.sources if not isinstance(source.get("id"), str) or not source.get("id")]
        if unidentified_sources:
            findings.append(_finding("fail", "clean-room-unidentified-source", "Clean-room evaluation contains source records without stable ids.", "Assign stable ids to every accessed source."))
        disallowed = sorted(known_sources - allowed_sources)
        if disallowed:
            findings.append(_finding("fail", "clean-room-source-leakage", f"Clean-room evaluation accessed disallowed source ids: {', '.join(disallowed)}.", "Remove disallowed sources and rerun in a clean environment."))

    return findings


def _evaluate_metrics_and_cost(manifest: ScientificRunManifest) -> list[GateFinding]:
    findings: list[GateFinding] = []
    if not manifest.token_economy:
        findings.append(_finding("warn", "missing-token-economy", "No Token Economy decision was attached.", "Attach draft lane, context budget, saved tokens, confidence floor, and escalation status."))
    else:
        required = ("draft_lane", "context_budget", "estimated_saved_context_tokens", "confidence_floor", "verification_spans")
        missing = [key for key in required if key not in manifest.token_economy]
        if missing:
            findings.append(_finding("warn", "incomplete-token-economy", f"Token Economy metadata is missing: {', '.join(missing)}.", "Record the complete Token Economy plan."))

    if manifest.workflow_stage in {"experimentation", "analysis", "deployment"} and not manifest.metrics:
        findings.append(_finding("fail", "missing-metrics", "Executable scientific work has no metrics.", "Record task metrics, benchmark scores, or validation results."))
    if manifest.claims_state_of_art and not manifest.heldout_eval:
        findings.append(_finding("fail", "state-of-art-without-heldout", "A state-of-the-art claim lacks held-out evaluation.", "Add held-out validation before making the public claim."))
    return findings


def _evaluate_privacy_and_claims(manifest: ScientificRunManifest) -> list[GateFinding]:
    findings: list[GateFinding] = []
    lane = _token_lane(manifest.token_economy)
    if manifest.contains_phi and lane.startswith("remote"):
        findings.append(_finding("fail", "phi-remote-lane", "PHI-bearing work is routed to a remote lane.", "Route PHI to local or institution-approved models only."))
    if manifest.contains_phi:
        findings.append(_finding("warn", "phi-private-output", "PHI-bearing work must not be published publicly.", "Keep the run private and audit-scoped."))
    if manifest.claims_autonomous_discovery and not manifest.human_reviewed:
        findings.append(_finding("fail", "autonomy-without-review", "Autonomous discovery claim lacks human review.", "Add expert review before publishing autonomous-science language."))
    if manifest.risk in {"high", "critical"} and not manifest.human_reviewed:
        findings.append(_finding("warn", "high-risk-no-human-review", "High-risk scientific work has no human review flag.", "Add human review before deployment or publication."))
    return findings


def manifest_from_evidence_trace(
    *,
    run_id: str,
    task_id: str,
    question: str,
    hypothesis: str,
    workflow_stage: WorkflowStage,
    evidence_trace: dict[str, Any],
    token_economy: dict[str, Any] | None = None,
    risk: RiskTier = "medium",
    **kwargs: Any,
) -> ScientificRunManifest:
    """Create a gate manifest from a Raven Evidence Graph packet."""

    sources = tuple(evidence_trace.get("sources", ()) or ())
    claims = evidence_trace.get("claims", ()) or ()
    claim_checks = tuple(
        ScientificClaimCheck(
            claim_id=str(claim.get("id", f"claim:{index}")),
            claim=str(claim.get("text", "")),
            evidence_label="support" if claim.get("source_ids") else "not_enough_information",
            source_ids=tuple(claim.get("source_ids", ()) or ()),
            confidence=float(claim.get("confidence", evidence_trace.get("confidence", 0.5))),
            rationale="Imported from Evidence Graph claim source linkage.",
        )
        for index, claim in enumerate(claims)
        if isinstance(claim, dict)
    )
    return ScientificRunManifest(
        run_id=run_id,
        task_id=task_id,
        question=question,
        hypothesis=hypothesis,
        workflow_stage=workflow_stage,
        risk=risk,
        sources=sources,
        claim_checks=claim_checks,
        token_economy=token_economy or {},
        evidence_trace=evidence_trace,
        **kwargs,
    )

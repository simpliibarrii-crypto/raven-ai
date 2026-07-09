from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Iterable

from runtime.scientific_agent_gates import (
    GateReport,
    ScientificClaimCheck,
    ScientificRunManifest,
    WorkflowStage,
    evaluate_scientific_run,
)

AgentRole = Literal[
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
]

ReceiptStatus = Literal["pass", "warn", "fail", "blocked", "not_run"]


@dataclass(frozen=True)
class SubagentSpec:
    """A narrow, auditable worker in the Raven lab loop."""

    name: str
    role: AgentRole
    objective: str
    required_evidence: tuple[str, ...] = ()
    escalation_trigger: str = "low confidence, missing evidence, privacy risk, or unsupported public claim"


@dataclass(frozen=True)
class ConnectorReceipt:
    """A compact receipt for work performed through an external surface."""

    surface: str
    status: ReceiptStatus
    summary: str
    evidence: tuple[str, ...] = ()
    measured_at: str | None = None
    notes: str = ""

    @property
    def source_id(self) -> str:
        normalized = self.surface.lower().replace(" ", "-").replace("/", "-")
        return f"connector:{normalized}"


@dataclass(frozen=True)
class LabLoopRun:
    """A full AI-led lab loop, from hypothesis to paper-grade evidence."""

    run_id: str
    task_id: str
    question: str
    hypothesis: str
    workflow_stage: WorkflowStage
    risk: Literal["low", "medium", "high", "critical"] = "medium"
    subagents: tuple[SubagentSpec, ...] = field(default_factory=tuple)
    connector_receipts: tuple[ConnectorReceipt, ...] = field(default_factory=tuple)
    claims: tuple[str, ...] = field(default_factory=tuple)
    metrics: dict[str, float | int | str] = field(default_factory=dict)
    token_economy: dict[str, Any] = field(default_factory=dict)
    evidence_trace: dict[str, Any] = field(default_factory=dict)
    code_artifacts: tuple[str, ...] = field(default_factory=tuple)
    output_artifacts: tuple[str, ...] = field(default_factory=tuple)
    replay_command: str | None = None
    environment_fingerprint: str | None = None
    heldout_eval: bool = False
    human_reviewed: bool = False
    contains_phi: bool = False
    claims_state_of_art: bool = False
    claims_autonomous_discovery: bool = False
    notes: str = ""


DEFAULT_SUBAGENTS: tuple[SubagentSpec, ...] = (
    SubagentSpec(
        name="Research Scout",
        role="intake",
        objective="Collect user intent, source links, repo context, and constraints before implementation.",
        required_evidence=("source URL", "repo list", "scope note"),
    ),
    SubagentSpec(
        name="Hypothesis Architect",
        role="hypothesis",
        objective="Convert the request into a falsifiable hypothesis and success criteria.",
        required_evidence=("research question", "hypothesis", "expected metric"),
    ),
    SubagentSpec(
        name="Protocol Planner",
        role="planning",
        objective="Break the run into repeatable steps with inputs, outputs, tools, and replay commands.",
        required_evidence=("protocol", "replay command", "environment fingerprint"),
    ),
    SubagentSpec(
        name="Sandbox Executor",
        role="execution",
        objective="Run the smallest safe experiment in Replit, local test, CI, or another approved sandbox.",
        required_evidence=("execution receipt", "logs", "artifacts"),
    ),
    SubagentSpec(
        name="Evidence Graph Curator",
        role="evidence",
        objective="Attach every claim to sources, metrics, and provenance using Raven Evidence Graph.",
        required_evidence=("raven.evidence_graph.v1", "claim ids", "source ids"),
    ),
    SubagentSpec(
        name="Verification Critic",
        role="verification",
        objective="Challenge weak claims, missing sources, low confidence, and insufficient test coverage.",
        required_evidence=("claim checks", "contradictions", "confidence floors"),
    ),
    SubagentSpec(
        name="Safety Guardian",
        role="safety",
        objective="Block PHI leakage, unsafe biosecurity claims, medical-device claims, and unsupported autonomy language.",
        required_evidence=("privacy route", "risk tier", "human review flag"),
    ),
    SubagentSpec(
        name="Metrics Accountant",
        role="metrics",
        objective="Record accuracy, latency, cost, token savings, test counts, and deployment outcomes.",
        required_evidence=("metrics", "cost estimate", "token economy"),
    ),
    SubagentSpec(
        name="Deployment Inspector",
        role="deployment",
        objective="Check Vercel, Hugging Face, GitHub, and demo surfaces for build health and public readiness.",
        required_evidence=("deployment receipt", "runtime error scan", "public URL"),
    ),
    SubagentSpec(
        name="Paper Scribe",
        role="paper",
        objective="Turn the run into a restrained scientific paper draft with methods, results, limits, and next tests.",
        required_evidence=("paper draft", "test table", "limitations"),
    ),
    SubagentSpec(
        name="Distribution Editor",
        role="distribution",
        objective="Prepare truthful README, release notes, model card, and community updates without inflated claims.",
        required_evidence=("release notes", "README diff", "model card"),
    ),
    SubagentSpec(
        name="Red Team Auditor",
        role="red_team",
        objective="Triple-check the run from product, security, science, deployment, and public-claim perspectives.",
        required_evidence=("risk register", "blocking issues", "review decision"),
    ),
)


def default_subagents() -> tuple[SubagentSpec, ...]:
    """Return Raven's standard multi-agent review board."""

    return DEFAULT_SUBAGENTS


def subagents_by_role(role: AgentRole, subagents: Iterable[SubagentSpec] = DEFAULT_SUBAGENTS) -> tuple[SubagentSpec, ...]:
    """Select the agents assigned to one stage of the lab loop."""

    return tuple(agent for agent in subagents if agent.role == role)


def connector_receipt_sources(receipts: Iterable[ConnectorReceipt]) -> tuple[dict[str, Any], ...]:
    """Convert connector receipts into Evidence Graph compatible sources."""

    return tuple(
        {
            "id": receipt.source_id,
            "title": f"{receipt.surface} connector receipt",
            "kind": "connector-receipt",
            "quality": _receipt_quality(receipt.status),
            "metadata": {
                "status": receipt.status,
                "summary": receipt.summary,
                "evidence": list(receipt.evidence),
                "measured_at": receipt.measured_at,
                "notes": receipt.notes,
            },
        }
        for receipt in receipts
    )


def build_scientific_manifest(run: LabLoopRun) -> ScientificRunManifest:
    """Translate a lab-loop run into the existing Scientific Agent Gates contract."""

    sources = connector_receipt_sources(run.connector_receipts)
    source_ids = tuple(source["id"] for source in sources)
    claim_checks = tuple(
        ScientificClaimCheck(
            claim_id=f"claim:{index + 1}",
            claim=claim,
            evidence_label="support" if source_ids else "not_enough_information",
            source_ids=source_ids,
            confidence=_claim_confidence(run.connector_receipts),
            rationale="Imported from LabLoopRun connector receipts.",
        )
        for index, claim in enumerate(run.claims)
    )
    return ScientificRunManifest(
        run_id=run.run_id,
        task_id=run.task_id,
        question=run.question,
        hypothesis=run.hypothesis,
        workflow_stage=run.workflow_stage,
        risk=run.risk,
        sources=sources,
        claim_checks=claim_checks,
        code_artifacts=run.code_artifacts,
        output_artifacts=run.output_artifacts,
        metrics=run.metrics,
        token_economy=run.token_economy,
        evidence_trace=run.evidence_trace,
        replay_command=run.replay_command,
        environment_fingerprint=run.environment_fingerprint,
        heldout_eval=run.heldout_eval,
        human_reviewed=run.human_reviewed,
        contains_phi=run.contains_phi,
        claims_state_of_art=run.claims_state_of_art,
        claims_autonomous_discovery=run.claims_autonomous_discovery,
        notes=run.notes,
    )


def evaluate_lab_loop_run(run: LabLoopRun) -> GateReport:
    """Evaluate a lab-loop run for publishability and autorun safety."""

    return evaluate_scientific_run(build_scientific_manifest(run))


def _receipt_quality(status: ReceiptStatus) -> float:
    quality = {
        "pass": 0.9,
        "warn": 0.65,
        "blocked": 0.45,
        "not_run": 0.35,
        "fail": 0.2,
    }[status]
    return quality


def _claim_confidence(receipts: tuple[ConnectorReceipt, ...]) -> float:
    if not receipts:
        return 0.35
    score = sum(_receipt_quality(receipt.status) for receipt in receipts) / len(receipts)
    return round(max(0.35, min(0.92, score)), 2)

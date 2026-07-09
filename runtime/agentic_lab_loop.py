from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

from runtime.evidence_graph import EvidenceGraph
from runtime.scientific_agent_gates import GateReport, ScientificRunManifest, evaluate_scientific_run, manifest_from_evidence_trace
from runtime.token_economy import TokenEconomyRequest, plan_token_economy

ConnectorKind = Literal["github", "replit", "vercel", "linear", "huggingface", "manual"]
LoopStage = Literal["hypothesis", "planning", "execution", "verification", "report", "deployment"]
ReceiptStatus = Literal["pass", "warn", "fail", "paused", "not_available"]


@dataclass(frozen=True)
class SubAgentSpec:
    """A narrow reviewer or operator in the Raven lab-in-the-loop system."""

    name: str
    role: str
    stage: LoopStage
    checks: tuple[str, ...]
    publishes_claims: bool = False


@dataclass(frozen=True)
class ConnectorReceipt:
    """A replayable observation from a connector-backed test or inspection."""

    connector: ConnectorKind
    target: str
    observation: str
    status: ReceiptStatus = "warn"
    metrics: dict[str, float | int | str] = field(default_factory=dict)
    evidence_uri: str | None = None


@dataclass(frozen=True)
class LabLoopTask:
    """A software lab-loop task that can become a publishable run manifest."""

    task_id: str
    question: str
    hypothesis: str
    repo: str = "simpliibarrii-crypto/raven-ai"
    risk: Literal["low", "medium", "high", "critical"] = "medium"
    contains_phi: bool = False
    claims_autonomous_discovery: bool = False
    code_artifacts: tuple[str, ...] = ()
    output_artifacts: tuple[str, ...] = ()
    replay_command: str | None = None
    environment_fingerprint: str | None = None


@dataclass(frozen=True)
class LabLoopResult:
    """Bundled output of planning, evidence tracing, gates, and receipts."""

    task: LabLoopTask
    subagents: tuple[SubAgentSpec, ...]
    receipts: tuple[ConnectorReceipt, ...]
    evidence_trace: dict[str, Any]
    token_economy: dict[str, Any]
    manifest: ScientificRunManifest
    gate_report: GateReport

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "raven.agentic_lab_loop.v1",
            "task": asdict(self.task),
            "subagents": [asdict(agent) for agent in self.subagents],
            "receipts": [asdict(receipt) for receipt in self.receipts],
            "evidence_trace": self.evidence_trace,
            "token_economy": self.token_economy,
            "manifest": asdict(self.manifest),
            "gate_report": asdict(self.gate_report),
        }


DEFAULT_SUBAGENTS: tuple[SubAgentSpec, ...] = (
    SubAgentSpec("hypothesis-cartographer", "turns intent into a falsifiable question", "hypothesis", ("question recorded", "hypothesis recorded")),
    SubAgentSpec("literature-scout", "collects prior work and public technical anchors", "planning", ("sources attached", "novelty scoped")),
    SubAgentSpec("protocol-architect", "designs the executable loop and replay command", "planning", ("replay command", "environment fingerprint")),
    SubAgentSpec("biosecurity-sentinel", "blocks unsafe biology, PHI, or overbroad clinical claims", "verification", ("PHI lane", "biosecurity language", "clinical scope")),
    SubAgentSpec("code-forge", "maps the plan into dependency-light code artifacts", "execution", ("module exists", "interfaces stable")),
    SubAgentSpec("sandbox-runner", "checks Replit or local sandbox execution receipts", "execution", ("sandbox response", "paused or pass recorded")),
    SubAgentSpec("ci-oracle", "reviews GitHub tests, lint, and workflow receipts", "verification", ("tests recorded", "CI status recorded")),
    SubAgentSpec("vercel-probe", "checks deployment readiness and runtime errors", "deployment", ("deployment list", "runtime error scan")),
    SubAgentSpec("linear-spine", "turns findings into roadmap issues and status docs", "planning", ("project exists", "milestones attached")),
    SubAgentSpec("huggingface-curator", "checks model and Space metadata before release", "deployment", ("repo metadata", "README alignment")),
    SubAgentSpec("statistician", "separates measured results from unsupported claims", "verification", ("metrics present", "no state-of-art without heldout")),
    SubAgentSpec("red-team-critic", "attacks the conclusion from safety and reproducibility angles", "verification", ("contradictions", "missing evidence")),
    SubAgentSpec("paper-scribe", "drafts restrained scientific prose from receipts only", "report", ("methods", "limitations", "results"), publishes_claims=True),
    SubAgentSpec("release-notary", "prepares public release packet and merge notes", "deployment", ("PR branch", "release checklist")),
)


def plan_lab_loop(task: LabLoopTask, receipts: tuple[ConnectorReceipt, ...] = ()) -> LabLoopResult:
    """Build an evidence-backed lab-loop result from connector receipts.

    This does not run wet-lab work. It converts software and connector observations
    into a Raven Evidence Graph, Token Economy plan, Scientific Agent Gate manifest,
    and paper-ready receipt bundle.
    """

    graph = EvidenceGraph()
    claim_ids: list[str] = []

    task_source = graph.add_source(
        title=f"Lab loop task {task.task_id}",
        kind="protocol",
        uri=task.repo,
        quality=0.74,
        metadata={"stage": "hypothesis"},
    )
    claim_ids.append(graph.add_claim(f"Research question: {task.question}", (task_source.id,), 0.82, task.risk, ("question",)).id)
    claim_ids.append(graph.add_claim(f"Hypothesis: {task.hypothesis}", (task_source.id,), 0.78, task.risk, ("hypothesis",)).id)

    for receipt in receipts:
        quality = receipt_quality(receipt.status)
        source = graph.add_source(
            title=f"{receipt.connector}:{receipt.target}",
            kind="connector_receipt",
            uri=receipt.evidence_uri,
            quality=quality,
            metadata={"connector": receipt.connector, "status": receipt.status, "metrics": receipt.metrics},
        )
        claim_ids.append(
            graph.add_claim(
                f"{receipt.connector} receipt for {receipt.target}: {receipt.observation}",
                (source.id,),
                quality,
                "medium" if receipt.status in {"warn", "paused"} else task.risk,
                ("connector-receipt", receipt.status),
            ).id
        )

    answer = (
        "Raven can represent an AI-led software lab loop when hypothesis, sandbox execution, "
        "connector receipts, Evidence Graph traces, Token Economy metadata, and Scientific Agent Gates "
        "are bundled before any public claim is made."
    )
    trace = graph.trace_answer(answer, claim_ids)
    evidence_trace = graph.to_dict()
    evidence_trace["answer_trace"] = asdict(trace)

    token_plan = plan_token_economy(
        TokenEconomyRequest(
            task=task.question,
            complexity="research",
            risk=task.risk,
            privacy="phi" if task.contains_phi else "public",
            estimated_context_tokens=24000,
            estimated_output_tokens=1600,
            cache_hit_ratio=0.35,
            draft_confidence=0.64,
            evidence_coverage=min(1.0, 0.2 + (0.1 * len(receipts))),
            requires_exact_citations=True,
            tool_available=True,
            local_model_available=True,
        )
    )
    token_economy = asdict(token_plan)
    token_economy["verification_spans"] = [agent.name for agent in DEFAULT_SUBAGENTS if agent.stage == "verification"]

    manifest = manifest_from_evidence_trace(
        run_id=f"lab-loop:{task.task_id}",
        task_id=task.task_id,
        question=task.question,
        hypothesis=task.hypothesis,
        workflow_stage="analysis",
        evidence_trace=evidence_trace,
        token_economy=token_economy,
        risk=task.risk,
        code_artifacts=task.code_artifacts or ("runtime/agentic_lab_loop.py",),
        output_artifacts=task.output_artifacts or ("docs/PAPER_AGENTIC_LAB_LOOP.md", "docs/CONNECTOR_TEST_RECEIPTS.md"),
        metrics=aggregate_receipt_metrics(receipts),
        replay_command=task.replay_command or "pytest -q tests/test_agentic_lab_loop.py",
        environment_fingerprint=task.environment_fingerprint or "python=3.11;pytest=8;dependency-free-runtime=true",
        heldout_eval=False,
        human_reviewed=True,
        contains_phi=task.contains_phi,
        claims_autonomous_discovery=task.claims_autonomous_discovery,
        notes="Software lab-loop receipt bundle. No wet-lab or clinical deployment claim is made.",
    )

    return LabLoopResult(
        task=task,
        subagents=DEFAULT_SUBAGENTS,
        receipts=receipts,
        evidence_trace=evidence_trace,
        token_economy=token_economy,
        manifest=manifest,
        gate_report=evaluate_scientific_run(manifest),
    )


def receipt_quality(status: ReceiptStatus) -> float:
    return {"pass": 0.86, "warn": 0.62, "paused": 0.55, "not_available": 0.42, "fail": 0.22}[status]


def aggregate_receipt_metrics(receipts: tuple[ConnectorReceipt, ...]) -> dict[str, float | int | str]:
    counts = {"pass": 0, "warn": 0, "fail": 0, "paused": 0, "not_available": 0}
    for receipt in receipts:
        counts[receipt.status] += 1
    total = len(receipts)
    passing = counts["pass"]
    return {
        "connector_receipts": total,
        "passing_receipts": passing,
        "warning_receipts": counts["warn"],
        "paused_receipts": counts["paused"],
        "failed_receipts": counts["fail"],
        "not_available_receipts": counts["not_available"],
        "receipt_pass_rate": round(passing / total, 3) if total else 0.0,
    }

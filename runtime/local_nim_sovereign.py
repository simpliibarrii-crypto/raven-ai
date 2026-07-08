"""Local NVIDIA NIM sovereign-agent adapter for Raven.

This module turns a local OpenAI-compatible NVIDIA NIM endpoint into a Raven
run packet with Evidence Graph tracing, Token Economy metadata, and a Scientific
Gate report. It intentionally avoids a LangChain dependency so Raven can keep
this lane lightweight and usable in sovereign/on-prem deployments.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import hashlib
import json
from typing import Any, Protocol

import httpx

from runtime.evidence_graph import EvidenceGraph
from runtime.scientific_agent_gates import (
    GateReport,
    evaluate_scientific_run,
    manifest_from_evidence_trace,
)
from runtime.token_economy import TokenEconomyRequest, TokenEconomyPlan, plan_token_economy


class NIMCompletionClient(Protocol):
    """Small protocol so tests and alternate clients can replace HTTP calls."""

    def complete(
        self,
        messages: list[dict[str, str]],
        *,
        max_tokens: int,
        temperature: float,
    ) -> str:
        """Return the assistant text for a chat-completion style request."""


@dataclass(frozen=True)
class LocalNIMConfig:
    """Connection settings for a local or institution-hosted NIM endpoint."""

    base_url: str = "http://localhost:8000/v1"
    model: str = "meta/llama-3.1-70b-instruct"
    timeout_seconds: float = 60.0
    max_tokens: int = 768
    temperature: float = 0.1


class LocalNIMError(RuntimeError):
    """Raised when the local NIM endpoint cannot produce a usable answer."""


class LocalNIMClient:
    """Tiny OpenAI-compatible client for local NVIDIA NIM chat endpoints."""

    def __init__(self, config: LocalNIMConfig) -> None:
        self.config = config

    def complete(
        self,
        messages: list[dict[str, str]],
        *,
        max_tokens: int,
        temperature: float,
    ) -> str:
        url = f"{self.config.base_url.rstrip('/')}/chat/completions"
        payload = {
            "model": self.config.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        try:
            response = httpx.post(url, json=payload, timeout=self.config.timeout_seconds)
            response.raise_for_status()
        except httpx.HTTPError as exc:  # pragma: no cover - exercised by integration environments
            raise LocalNIMError(f"Local NIM request failed: {exc}") from exc

        data = response.json()
        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LocalNIMError("Local NIM response did not include choices[0].message.content.") from exc
        if not isinstance(content, str) or not content.strip():
            raise LocalNIMError("Local NIM returned an empty answer.")
        return content.strip()


@dataclass(frozen=True)
class NIMSource:
    """Source material provided to the sovereign-agent run."""

    title: str
    text: str
    kind: str = "document"
    uri: str | None = None
    quality: float = 0.75
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SovereignAgentResult:
    """Complete Raven packet for a local NIM run."""

    run_id: str
    answer: str
    evidence_graph: dict[str, Any]
    evidence_trace: dict[str, Any]
    token_economy: dict[str, Any]
    gate_report: GateReport

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "answer": self.answer,
            "evidence_graph": self.evidence_graph,
            "evidence_trace": self.evidence_trace,
            "token_economy": self.token_economy,
            "gate_report": asdict(self.gate_report),
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, sort_keys=True)


def run_local_nim_sovereign_agent(
    *,
    question: str,
    sources: list[NIMSource] | tuple[NIMSource, ...],
    hypothesis: str = "A local NIM answer can be made reviewable with Raven Evidence Graph tracing.",
    task_id: str = "local-nim-sovereign-agent",
    client: NIMCompletionClient | None = None,
    config: LocalNIMConfig | None = None,
    contains_phi: bool = False,
    human_reviewed: bool = False,
) -> SovereignAgentResult:
    """Run a local NIM answer and wrap it in Raven evidence and gate metadata.

    The function is suitable for synthetic demos and on-prem deployments. If
    `contains_phi=True`, the Scientific Gate report will prevent public release.
    """

    if not question.strip():
        raise ValueError("question must not be empty")
    if not sources:
        raise ValueError("at least one source is required")

    config = config or LocalNIMConfig()
    client = client or LocalNIMClient(config)

    evidence_graph = EvidenceGraph()
    all_claim_ids: list[str] = []
    source_digest_parts: list[str] = []
    for source in sources:
        if not source.text.strip():
            raise ValueError(f"source {source.title!r} has no text")
        claims = evidence_graph.ingest_document(
            title=source.title,
            text=source.text,
            kind=source.kind,
            uri=source.uri,
            quality=source.quality,
            labels=("local-nim-context",),
            max_claims=8,
        )
        all_claim_ids.extend(claim.id for claim in claims)
        source_digest_parts.append(f"{source.title}:{source.text[:160]}")

    token_request = TokenEconomyRequest(
        task=question,
        complexity="hard" if contains_phi else "standard",
        risk="high" if contains_phi else "medium",
        privacy="phi" if contains_phi else "private",
        estimated_context_tokens=sum(max(1, len(source.text.split())) for source in sources) * 2,
        estimated_output_tokens=config.max_tokens,
        draft_confidence=0.72,
        evidence_coverage=0.8 if all_claim_ids else 0.0,
        local_model_available=True,
        latency_sensitive=True,
        requires_exact_citations=True,
    )
    token_plan = plan_token_economy(token_request)

    answer = client.complete(
        _messages(question=question, sources=sources, token_plan=token_plan),
        max_tokens=token_plan.max_output_tokens,
        temperature=config.temperature,
    )

    answer_claim = evidence_graph.add_claim(
        answer,
        source_ids=evidence_graph.to_dict()["sources"][:1][0:1] and [evidence_graph.to_dict()["sources"][0]["id"]],
        confidence=max(token_plan.confidence_floor, 0.58),
        risk="high" if contains_phi else "medium",
        labels=("local-nim-answer",),
    )
    trace = evidence_graph.trace_answer(answer, [*all_claim_ids[:6], answer_claim.id])
    graph_packet = evidence_graph.to_dict()
    evidence_trace = {
        "schema": graph_packet["schema"],
        "question": question,
        "answer": trace.answer,
        "claim_ids": trace.claim_ids,
        "source_ids": trace.source_ids,
        "confidence": trace.confidence,
        "risk": trace.risk,
        "explanation": trace.explanation,
    }

    token_metadata = _token_plan_metadata(token_plan)
    run_id = stable_run_id(question, source_digest_parts, config.model)
    manifest = manifest_from_evidence_trace(
        run_id=run_id,
        task_id=task_id,
        question=question,
        hypothesis=hypothesis,
        workflow_stage="analysis",
        evidence_trace=graph_packet,
        token_economy=token_metadata,
        risk="high" if contains_phi else "medium",
        code_artifacts=("runtime/local_nim_sovereign.py",),
        output_artifacts=(f"{run_id}.json",),
        metrics={"source_count": len(sources), "claim_count": len(graph_packet["claims"])},
        replay_command="python examples/local_nim_sovereign_agent.py",
        environment_fingerprint=f"nim:{config.model}@{config.base_url}",
        contains_phi=contains_phi,
        human_reviewed=human_reviewed,
        notes="Local NIM lane; publish only after reviewing source material and gate report.",
    )
    gate_report = evaluate_scientific_run(manifest)
    return SovereignAgentResult(
        run_id=run_id,
        answer=answer,
        evidence_graph=graph_packet,
        evidence_trace=evidence_trace,
        token_economy=token_metadata,
        gate_report=gate_report,
    )


def _messages(
    *,
    question: str,
    sources: list[NIMSource] | tuple[NIMSource, ...],
    token_plan: TokenEconomyPlan,
) -> list[dict[str, str]]:
    context = "\n\n".join(f"Source {index + 1}: {source.title}\n{source.text}" for index, source in enumerate(sources))
    return [
        {
            "role": "system",
            "content": (
                "You are Raven AI running through a local sovereign NIM lane. "
                "Answer from the provided sources only. State uncertainty. "
                "Do not provide medical instructions or pretend clinical validation."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Question: {question}\n\n"
                f"Token Economy lane: {token_plan.draft_lane}; confidence floor: {token_plan.confidence_floor}.\n\n"
                f"Sources:\n{context}"
            ),
        },
    ]


def _token_plan_metadata(plan: TokenEconomyPlan) -> dict[str, Any]:
    return {
        "draft_lane": plan.draft_lane,
        "thinking_level": plan.thinking_level,
        "context_budget": plan.context_budget,
        "draft_token_budget": plan.draft_token_budget,
        "verification_token_budget": plan.verification_token_budget,
        "max_output_tokens": plan.max_output_tokens,
        "estimated_saved_context_tokens": plan.estimated_saved_context_tokens,
        "should_escalate": plan.should_escalate,
        "confidence_floor": plan.confidence_floor,
        "verification_spans": list(plan.actions),
        "reason": plan.reason,
    }


def stable_run_id(question: str, source_digest_parts: list[str], model: str) -> str:
    digest = hashlib.sha256("|".join([question, model, *source_digest_parts]).encode("utf-8")).hexdigest()[:12]
    return f"local-nim:{digest}"

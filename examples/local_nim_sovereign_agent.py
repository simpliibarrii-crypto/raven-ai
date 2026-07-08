"""Local NVIDIA NIM + Raven Evidence Graph reference example.

This example adapts the `langchain-nvidia` fork branch
`feat/local-nim-sovereign-agent-example` into Raven's own contracts.

Purpose
-------
Show how a sovereign/local NIM lane can produce:

- a Raven Evidence Graph packet,
- Token Economy routing metadata,
- a Scientific Gates report,
- replayable JSON artifacts.

It is intentionally optional. Raven core remains dependency-light; LangChain,
LangGraph, and langchain-nvidia-ai-endpoints are imported only inside the NIM
runner.

Run with a local NIM-compatible endpoint:

    python examples/local_nim_sovereign_agent.py \
      --base-url http://localhost:8000/v1 \
      --model meta/llama-3.1-70b-instruct \
      --question "Summarize this synthetic handoff note safely." \
      --source-text "Synthetic note: resident reports poor sleep and mild cough. No PHI."

This file does not claim clinical validation. It demonstrates trace mechanics.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import platform
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime.evidence_graph import EvidenceGraph
from runtime.scientific_agent_gates import (
    evaluate_scientific_run,
    manifest_from_evidence_trace,
)
from runtime.token_economy import TokenEconomyRequest, plan_token_economy


def _dataclass_to_dict(value: Any) -> Any:
    if dataclasses.is_dataclass(value):
        return dataclasses.asdict(value)
    return value


def build_evidence_graph(*, question: str, answer: str, source_text: str) -> EvidenceGraph:
    """Create a Raven Evidence Graph from source text plus agent answer."""

    graph = EvidenceGraph()
    source = graph.add_source(
        title="Synthetic local NIM source packet",
        kind="synthetic_note",
        uri="local://nim-demo/synthetic-note",
        quality=0.72,
        metadata={
            "demo": True,
            "contains_phi": False,
            "question": question,
        },
    )
    graph.ingest_document(
        title="Synthetic local NIM source packet",
        text=source_text,
        kind="synthetic_note",
        uri="local://nim-demo/synthetic-note",
        quality=0.72,
        labels=("synthetic", "local-nim", "source"),
        max_claims=6,
    )
    graph.add_claim(
        answer,
        source_ids=[source.id],
        confidence=0.68,
        risk="medium",
        labels=("agent-output", "local-nim"),
    )
    return graph


def build_token_plan(question: str) -> dict[str, Any]:
    """Plan a sovereign/local route for the NIM-backed answer."""

    plan = plan_token_economy(
        TokenEconomyRequest(
            task=question,
            complexity="standard",
            risk="medium",
            privacy="private",
            estimated_context_tokens=4_000,
            estimated_output_tokens=768,
            cache_hit_ratio=0.15,
            draft_confidence=0.68,
            evidence_coverage=0.72,
            latency_sensitive=True,
            requires_exact_citations=True,
            tool_available=False,
            local_model_available=True,
        )
    )
    data = _dataclass_to_dict(plan)
    data["verification_spans"] = ["agent answer", "source linkage", "public wording"]
    data["provider_lane"] = "local_nim"
    data["sovereign_mode"] = True
    return data


def call_local_nim(*, base_url: str, model: str, question: str, source_text: str) -> str:
    """Call a local NIM-compatible endpoint through LangChain NVIDIA.

    The import is lazy so Raven core does not gain a hard dependency on
    langchain-nvidia-ai-endpoints.
    """

    try:
        from langchain_nvidia_ai_endpoints import ChatNVIDIA
        from langchain_core.messages import HumanMessage, SystemMessage
    except ImportError as exc:  # pragma: no cover - depends on optional packages
        raise RuntimeError(
            "Install optional NIM demo dependencies first: "
            "pip install langchain-nvidia-ai-endpoints langchain-core"
        ) from exc

    llm = ChatNVIDIA(
        base_url=base_url,
        model=model,
        temperature=0.1,
        max_tokens=768,
    )
    messages = [
        SystemMessage(
            content=(
                "You are a cautious Raven AI sovereign-agent demo. "
                "Use only the provided synthetic source text. "
                "Do not make clinical recommendations. State limitations clearly."
            )
        ),
        HumanMessage(content=f"Question: {question}\n\nSource text:\n{source_text}"),
    ]
    response = llm.invoke(messages)
    return str(response.content)


def build_gate_report(
    *,
    question: str,
    evidence_packet: dict[str, Any],
    token_plan: dict[str, Any],
    output_path: Path,
) -> dict[str, Any]:
    """Evaluate the run with Raven Scientific Gates."""

    manifest = manifest_from_evidence_trace(
        run_id="local-nim-sovereign-demo",
        task_id="raven.local_nim_sovereign_agent.v1",
        question=question,
        hypothesis="A local NIM-backed agent can emit a Raven Evidence Graph trace for review.",
        workflow_stage="analysis",
        evidence_trace=evidence_packet,
        token_economy=token_plan,
        risk="medium",
        code_artifacts=("examples/local_nim_sovereign_agent.py",),
        output_artifacts=(str(output_path),),
        metrics={
            "evidence_sources": len(evidence_packet.get("sources", [])),
            "evidence_claims": len(evidence_packet.get("claims", [])),
        },
        replay_command=(
            "python examples/local_nim_sovereign_agent.py "
            "--base-url http://localhost:8000/v1 "
            "--model meta/llama-3.1-70b-instruct"
        ),
        environment_fingerprint=f"python={platform.python_version()}; platform={platform.platform()}",
        human_reviewed=False,
        contains_phi=False,
        claims_state_of_art=False,
        claims_autonomous_discovery=False,
        notes="Reference demo only. Uses synthetic source text and requires human review before public claims.",
    )
    return dataclasses.asdict(evaluate_scientific_run(manifest))


def run_demo(args: argparse.Namespace) -> dict[str, Any]:
    answer = call_local_nim(
        base_url=args.base_url,
        model=args.model,
        question=args.question,
        source_text=args.source_text,
    )
    graph = build_evidence_graph(question=args.question, answer=answer, source_text=args.source_text)
    evidence_packet = graph.to_dict()
    token_plan = build_token_plan(args.question)

    output_path = Path(args.output).resolve()
    gate_report = build_gate_report(
        question=args.question,
        evidence_packet=evidence_packet,
        token_plan=token_plan,
        output_path=output_path,
    )
    artifact = {
        "schema": "raven.local_nim_sovereign_agent.demo.v1",
        "question": args.question,
        "answer": answer,
        "nim": {"base_url": args.base_url, "model": args.model},
        "token_economy": token_plan,
        "evidence_trace": evidence_packet,
        "gate_report": gate_report,
        "limitations": [
            "Reference example only.",
            "Requires a reachable local NIM-compatible endpoint.",
            "Uses synthetic source text by default.",
            "Does not establish clinical validation or medical-device readiness.",
        ],
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(artifact, indent=2, sort_keys=True), encoding="utf-8")
    return artifact


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a local NIM sovereign Raven agent demo.")
    parser.add_argument("--base-url", default="http://localhost:8000/v1")
    parser.add_argument("--model", default="meta/llama-3.1-70b-instruct")
    parser.add_argument(
        "--question",
        default="Summarize this synthetic handoff note safely and state limitations.",
    )
    parser.add_argument(
        "--source-text",
        default="Synthetic note: resident reports poor sleep and mild cough. No PHI is included.",
    )
    parser.add_argument("--output", default="artifacts/local_nim_sovereign_agent.json")
    return parser.parse_args()


if __name__ == "__main__":
    result = run_demo(parse_args())
    print(json.dumps({"output_schema": result["schema"], "gate_status": result["gate_report"]["status"]}, indent=2))

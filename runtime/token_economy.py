from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal

Complexity = Literal["trivial", "simple", "standard", "hard", "research"]
Risk = Literal["low", "medium", "high", "critical"]
Privacy = Literal["public", "internal", "private", "phi"]
ThinkingLevel = Literal["off", "low", "medium", "high", "max"]
DraftLane = Literal["cache", "tool", "local-small", "local-large", "remote-cheap", "remote-strong"]

RISK_WEIGHT: dict[Risk, float] = {"low": 0.0, "medium": 0.33, "high": 0.72, "critical": 1.0}
COMPLEXITY_WEIGHT: dict[Complexity, float] = {
    "trivial": 0.0,
    "simple": 0.2,
    "standard": 0.45,
    "hard": 0.75,
    "research": 1.0,
}


@dataclass(frozen=True)
class TokenEconomyRequest:
    """Inputs Raven knows before spending tokens on an agent/model call."""

    task: str
    complexity: Complexity = "standard"
    risk: Risk = "medium"
    privacy: Privacy = "public"
    estimated_context_tokens: int = 0
    estimated_output_tokens: int = 512
    cache_hit_ratio: float = 0.0
    draft_confidence: float = 0.5
    evidence_coverage: float = 0.0
    system_load: float = 0.0
    latency_sensitive: bool = False
    requires_exact_citations: bool = False
    tool_available: bool = False
    local_model_available: bool = True


@dataclass(frozen=True)
class TokenEconomyPlan:
    """A model-agnostic token budget and verification plan."""

    draft_lane: DraftLane
    thinking_level: ThinkingLevel
    context_budget: int
    draft_token_budget: int
    verification_token_budget: int
    max_output_tokens: int
    estimated_saved_context_tokens: int
    should_escalate: bool
    confidence_floor: float
    actions: tuple[str, ...]
    reason: str

    @property
    def total_generation_budget(self) -> int:
        return self.draft_token_budget + self.verification_token_budget + self.max_output_tokens


@dataclass(frozen=True)
class VerificationSpan:
    """A small work item for checking only the uncertain parts of a draft."""

    label: str
    confidence: float
    risk: Risk = "medium"
    evidence_coverage: float = 0.0


@dataclass(frozen=True)
class VerificationSchedule:
    spans_to_verify: tuple[VerificationSpan, ...]
    skipped_spans: tuple[VerificationSpan, ...]
    token_budget: int
    reason: str


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def estimate_survival_probability(request: TokenEconomyRequest) -> float:
    """Approximate whether a cheap draft will survive heavier verification."""

    confidence = clamp(request.draft_confidence)
    evidence = clamp(request.evidence_coverage)
    risk_penalty = RISK_WEIGHT[request.risk] * 0.24
    complexity_penalty = COMPLEXITY_WEIGHT[request.complexity] * 0.18
    citation_bonus = 0.06 if request.requires_exact_citations and evidence >= 0.75 else 0.0
    return clamp((confidence * 0.58) + (evidence * 0.36) + citation_bonus - risk_penalty - complexity_penalty)


def choose_thinking_level(request: TokenEconomyRequest) -> ThinkingLevel:
    if request.complexity == "trivial" and request.risk == "low":
        return "off"
    if request.privacy in {"private", "phi"} and request.risk in {"high", "critical"}:
        return "high"
    if request.complexity == "research" or request.risk == "critical":
        return "max"
    if request.complexity == "hard" or request.risk == "high" or request.requires_exact_citations:
        return "high"
    if request.complexity == "standard" or request.risk == "medium":
        return "medium"
    return "low"


def choose_draft_lane(request: TokenEconomyRequest) -> DraftLane:
    if request.cache_hit_ratio >= 0.8:
        return "cache"
    if request.tool_available and request.complexity in {"trivial", "simple", "standard"}:
        return "tool"
    if request.privacy in {"private", "phi"}:
        return "local-large" if request.risk in {"high", "critical"} else "local-small"
    if request.local_model_available and request.latency_sensitive:
        return "local-small"
    if request.complexity in {"hard", "research"} and request.risk in {"high", "critical"}:
        return "remote-strong"
    return "remote-cheap"


def plan_token_economy(request: TokenEconomyRequest) -> TokenEconomyPlan:
    """Plan Raven's token spend using DSpark-inspired draft/verify scheduling."""

    cache_hit_ratio = clamp(request.cache_hit_ratio)
    survival = estimate_survival_probability(request)
    thinking = choose_thinking_level(request)
    lane = choose_draft_lane(request)

    reusable_context = int(request.estimated_context_tokens * cache_hit_ratio)
    context_after_cache = max(0, request.estimated_context_tokens - reusable_context)

    if request.privacy in {"private", "phi"}:
        context_budget = min(context_after_cache, 24_000)
    elif request.complexity == "research":
        context_budget = min(context_after_cache, 96_000)
    elif request.complexity == "hard":
        context_budget = min(context_after_cache, 48_000)
    else:
        context_budget = min(context_after_cache, 16_000)

    base_draft = max(64, min(request.estimated_output_tokens // 2, 768))
    if lane in {"cache", "tool"}:
        draft_budget = min(base_draft, 160)
    elif survival >= 0.7:
        draft_budget = min(base_draft, 384)
    else:
        draft_budget = min(base_draft, 256)

    verification_pressure = (
        (1.0 - survival) * 0.48
        + RISK_WEIGHT[request.risk] * 0.34
        + COMPLEXITY_WEIGHT[request.complexity] * 0.18
    )
    if request.requires_exact_citations:
        verification_pressure += 0.18
    if request.system_load >= 0.75 and request.risk in {"low", "medium"}:
        verification_pressure *= 0.75
    verification_pressure = clamp(verification_pressure)

    verification_budget = max(64, int(request.estimated_output_tokens * verification_pressure))
    if request.risk == "critical" or request.requires_exact_citations:
        verification_budget = max(verification_budget, min(request.estimated_output_tokens, 512))

    should_escalate = survival < 0.45 or request.risk == "critical" or request.complexity == "research"
    if request.privacy in {"private", "phi"}:
        should_escalate = False

    output_cap = request.estimated_output_tokens
    if thinking in {"off", "low"}:
        output_cap = min(output_cap, 512)
    elif thinking == "medium":
        output_cap = min(output_cap, 1_024)
    elif thinking == "high":
        output_cap = min(output_cap, 2_048)
    else:
        output_cap = min(output_cap, 4_096)

    actions = build_actions(request, lane, survival, context_budget, should_escalate)
    reason = build_reason(request, lane, survival, verification_budget, should_escalate)

    return TokenEconomyPlan(
        draft_lane=lane,
        thinking_level=thinking,
        context_budget=context_budget,
        draft_token_budget=draft_budget,
        verification_token_budget=verification_budget,
        max_output_tokens=output_cap,
        estimated_saved_context_tokens=reusable_context + max(0, context_after_cache - context_budget),
        should_escalate=should_escalate,
        confidence_floor=round(max(0.52, 1.0 - verification_pressure), 2),
        actions=actions,
        reason=reason,
    )


def build_actions(
    request: TokenEconomyRequest,
    lane: DraftLane,
    survival: float,
    context_budget: int,
    should_escalate: bool,
) -> tuple[str, ...]:
    actions: list[str] = []
    if request.cache_hit_ratio > 0:
        actions.append("reuse cached summaries before adding raw context")
    if context_budget < request.estimated_context_tokens:
        actions.append("retrieve narrow evidence slices instead of full documents")
    actions.append(f"draft first with {lane}")
    if survival >= 0.7 and request.risk in {"low", "medium"}:
        actions.append("verify only uncertain claims and citation edges")
    else:
        actions.append("verify claim spans with low confidence or weak evidence")
    if request.requires_exact_citations:
        actions.append("force citation-level evidence checks")
    if should_escalate:
        actions.append("escalate only after cheap draft fails confidence floor")
    if request.privacy in {"private", "phi"}:
        actions.append("keep private context on local or institution-approved models")
    return tuple(actions)


def build_reason(
    request: TokenEconomyRequest,
    lane: DraftLane,
    survival: float,
    verification_budget: int,
    should_escalate: bool,
) -> str:
    escalation = "escalation allowed" if should_escalate else "no remote escalation by default"
    return (
        f"Selected {lane} draft lane with survival={survival:.2f}, "
        f"risk={request.risk}, complexity={request.complexity}, "
        f"verification_budget={verification_budget}, {escalation}."
    )


def schedule_verification(
    spans: list[VerificationSpan] | tuple[VerificationSpan, ...],
    *,
    base_tokens_per_span: int = 96,
    system_load: float = 0.0,
) -> VerificationSchedule:
    """Schedule verification for the riskiest and least certain spans first."""

    ordered = sorted(
        spans,
        key=lambda span: (
            RISK_WEIGHT[span.risk] * 0.55
            + (1.0 - clamp(span.confidence)) * 0.35
            + (1.0 - clamp(span.evidence_coverage)) * 0.10
        ),
        reverse=True,
    )
    if not ordered:
        return VerificationSchedule((), (), 0, "No spans need verification.")

    pressure = 1.0 - (0.35 * clamp(system_load))
    keep_count = max(1, math.ceil(len(ordered) * pressure))
    critical = [span for span in ordered if span.risk == "critical"]
    selected = ordered[:keep_count]
    for span in critical:
        if span not in selected:
            selected.append(span)

    skipped = tuple(span for span in ordered if span not in selected)
    return VerificationSchedule(
        spans_to_verify=tuple(selected),
        skipped_spans=skipped,
        token_budget=len(selected) * base_tokens_per_span,
        reason="Confidence-scheduled verification prioritizes high-risk, low-confidence, low-evidence spans.",
    )

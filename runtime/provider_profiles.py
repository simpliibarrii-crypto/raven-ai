from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

Sensitivity = Literal["public", "internal", "private", "phi"]
ReasoningLevel = Literal["low", "medium", "high"]
BudgetLevel = Literal["lowest", "balanced", "premium"]


@dataclass(frozen=True)
class ModelProviderProfile:
    """Static model/provider capability profile used before live adapters exist."""

    id: str
    label: str
    provider: str
    model: str
    base_url: str | None
    context_tokens: int
    max_output_tokens: int | None
    supports_json: bool
    supports_tools: bool
    thinking_modes: tuple[str, ...] = ()
    acceleration: str | None = None
    hf_reference: str | None = None
    license: str | None = None
    best_for: tuple[str, ...] = ()
    avoid_for: tuple[str, ...] = ()
    notes: str = ""
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class ProviderRouteRequest:
    """Routing hints from an agent or workflow before a model call is made."""

    task: str
    context_tokens: int = 0
    reasoning: ReasoningLevel = "medium"
    latency_sensitive: bool = False
    budget: BudgetLevel = "balanced"
    sensitivity: Sensitivity = "public"
    requires_local: bool = False
    requires_json: bool = False
    requires_tools: bool = False


@dataclass(frozen=True)
class ProviderRouteDecision:
    profile: ModelProviderProfile
    reason: str
    requires_evidence_trace: bool = True


CHEAP_REMOTE_LANE = ModelProviderProfile(
    id="cheap-remote-lane",
    label="Cheap remote lane",
    provider="remote-generic",
    model="cheap-long-context-or-fast-reasoning",
    base_url=None,
    context_tokens=1_000_000,
    max_output_tokens=64_000,
    supports_json=True,
    supports_tools=True,
    thinking_modes=("low", "medium"),
    acceleration="Use the fastest/cost-effective approved provider available for the deployment.",
    best_for=(
        "cheap-first research reasoning",
        "long-context summarization after slicing",
        "agent planning drafts",
        "code and workflow drafting",
        "evidence graph source distillation",
    ),
    avoid_for=(
        "raw PHI or private patient data without an approved deployment boundary",
        "tasks that must run fully offline",
        "final clinical decisions",
    ),
    notes="Vendor-neutral default lane. Implementations may map this to OpenRouter, DeepSeek, Qwen, hosted open models, or another approved provider.",
)


STRONG_REMOTE_LANE = ModelProviderProfile(
    id="strong-remote-lane",
    label="Strong remote lane",
    provider="remote-generic",
    model="strong-reasoning-escalation",
    base_url=None,
    context_tokens=1_000_000,
    max_output_tokens=128_000,
    supports_json=True,
    supports_tools=True,
    thinking_modes=("high", "max"),
    acceleration="Use only after cheap draft, confidence scheduling, and policy checks indicate escalation is worth the cost.",
    best_for=(
        "hard reasoning escalation",
        "architecture planning",
        "complex code review",
        "multi-document synthesis",
    ),
    avoid_for=(
        "raw PHI or private patient data without an approved deployment boundary",
        "tasks that must run fully offline",
        "cheap high-volume traffic when a draft lane is sufficient",
    ),
    notes="Vendor-neutral escalation lane. The selected provider should be deployment-specific and policy-approved.",
)


LOCAL_FIRST_FALLBACK = ModelProviderProfile(
    id="local-first-fallback",
    label="Local-first fallback",
    provider="local",
    model="ollama-or-hermes-local",
    base_url=None,
    context_tokens=128_000,
    max_output_tokens=None,
    supports_json=False,
    supports_tools=True,
    best_for=("PHI", "private data", "offline work", "edge routing"),
    notes="Placeholder profile for Ollama, LM Studio, Hermes Edge, or an institution-approved local model.",
)


DEEPSEEK_V4_FLASH_DSPARK = ModelProviderProfile(
    id="deepseek-v4-flash-dspark",
    label="DeepSeek V4 Flash + DSpark reference",
    provider="deepseek",
    model="deepseek-v4-flash",
    base_url="https://api.deepseek.com",
    context_tokens=1_000_000,
    max_output_tokens=384_000,
    supports_json=True,
    supports_tools=True,
    thinking_modes=("thinking", "non-thinking"),
    acceleration="DSpark speculative decoding when served by DeepSeek or self-hosted through DeepSpec-compatible inference.",
    hf_reference="deepseek-ai/DeepSeek-V4-Flash-DSpark",
    license="MIT weights on Hugging Face; API terms may differ.",
    best_for=("research reference", "optional cheap remote lane implementation"),
    avoid_for=("default product identity", "PHI/private data by default"),
    notes="Research reference only. Raven Token Economy should not depend on this provider directly.",
)


DEEPSEEK_V4_PRO_DSPARK = ModelProviderProfile(
    id="deepseek-v4-pro-dspark",
    label="DeepSeek V4 Pro + DSpark reference",
    provider="deepseek",
    model="deepseek-v4-pro",
    base_url="https://api.deepseek.com",
    context_tokens=1_000_000,
    max_output_tokens=384_000,
    supports_json=True,
    supports_tools=True,
    thinking_modes=("thinking", "non-thinking"),
    acceleration="DSpark speculative decoding when served by DeepSeek or self-hosted through DeepSpec-compatible inference.",
    hf_reference="deepseek-ai/DeepSeek-V4-Pro-DSpark",
    license="MIT weights on Hugging Face; API terms may differ.",
    best_for=("research reference", "optional strong remote lane implementation"),
    avoid_for=("default product identity", "PHI/private data by default"),
    notes="Research reference only. Raven Token Economy should not depend on this provider directly.",
)


DEFAULT_PROFILES: tuple[ModelProviderProfile, ...] = (
    CHEAP_REMOTE_LANE,
    STRONG_REMOTE_LANE,
    LOCAL_FIRST_FALLBACK,
)

REFERENCE_PROFILES: tuple[ModelProviderProfile, ...] = (
    DEEPSEEK_V4_FLASH_DSPARK,
    DEEPSEEK_V4_PRO_DSPARK,
)


def get_provider_profile(
    profile_id: str,
    profiles: tuple[ModelProviderProfile, ...] = DEFAULT_PROFILES + REFERENCE_PROFILES,
) -> ModelProviderProfile:
    for profile in profiles:
        if profile.id == profile_id:
            return profile
    raise KeyError(f"Unknown provider profile: {profile_id}")


def select_provider(request: ProviderRouteRequest) -> ProviderRouteDecision:
    """Select a provider lane using Raven's privacy-first routing posture."""

    if request.requires_local or request.sensitivity in {"private", "phi"}:
        return ProviderRouteDecision(
            profile=LOCAL_FIRST_FALLBACK,
            reason="Local route required because the request is private, PHI-bearing, or explicitly offline.",
        )

    if request.context_tokens > CHEAP_REMOTE_LANE.context_tokens:
        return ProviderRouteDecision(
            profile=LOCAL_FIRST_FALLBACK,
            reason="Context exceeds the configured remote lane window; segment locally before remote routing.",
        )

    if request.reasoning == "high" and request.budget != "lowest" and not request.latency_sensitive:
        return ProviderRouteDecision(
            profile=STRONG_REMOTE_LANE,
            reason="High-reasoning public/internal task can use the vendor-neutral strong escalation lane.",
        )

    if request.requires_json or request.requires_tools or request.latency_sensitive or request.budget in {"lowest", "balanced"}:
        return ProviderRouteDecision(
            profile=CHEAP_REMOTE_LANE,
            reason="Cheap remote lane is the default long-context draft route after policy checks pass.",
        )

    return ProviderRouteDecision(
        profile=CHEAP_REMOTE_LANE,
        reason="Default public/internal Raven draft route.",
    )


def evidence_trace_tags(decision: ProviderRouteDecision) -> tuple[str, ...]:
    """Tags to attach to Raven Evidence Graph traces for provider provenance."""

    return (
        f"provider:{decision.profile.provider}",
        f"model:{decision.profile.model}",
        f"profile:{decision.profile.id}",
    )

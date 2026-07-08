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


DEEPSEEK_V4_FLASH_DSPARK = ModelProviderProfile(
    id="deepseek-v4-flash-dspark",
    label="DeepSeek V4 Flash + DSpark",
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
    best_for=(
        "cheap-first research reasoning",
        "long-context summarization",
        "agent planning",
        "code and workflow drafting",
        "evidence graph source distillation",
    ),
    avoid_for=(
        "raw PHI or private patient data without an approved deployment boundary",
        "tasks that must run fully offline",
        "final clinical decisions",
    ),
    notes="Use as Raven's default remote long-context reasoning profile after local/privacy checks pass.",
)


DEEPSEEK_V4_PRO_DSPARK = ModelProviderProfile(
    id="deepseek-v4-pro-dspark",
    label="DeepSeek V4 Pro + DSpark",
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
    best_for=(
        "hard reasoning escalation",
        "architecture planning",
        "complex code review",
        "multi-document synthesis",
    ),
    avoid_for=(
        "raw PHI or private patient data without an approved deployment boundary",
        "tasks that must run fully offline",
        "cheap high-volume traffic when Flash is sufficient",
    ),
    notes="Use as an escalation route when Flash is not enough and the workflow allows remote inference.",
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


DEFAULT_PROFILES: tuple[ModelProviderProfile, ...] = (
    DEEPSEEK_V4_FLASH_DSPARK,
    DEEPSEEK_V4_PRO_DSPARK,
    LOCAL_FIRST_FALLBACK,
)


def get_provider_profile(profile_id: str, profiles: tuple[ModelProviderProfile, ...] = DEFAULT_PROFILES) -> ModelProviderProfile:
    for profile in profiles:
        if profile.id == profile_id:
            return profile
    raise KeyError(f"Unknown provider profile: {profile_id}")


def select_provider(request: ProviderRouteRequest) -> ProviderRouteDecision:
    """Select a safe provider profile using Raven's privacy-first routing posture."""

    if request.requires_local or request.sensitivity in {"private", "phi"}:
        return ProviderRouteDecision(
            profile=LOCAL_FIRST_FALLBACK,
            reason="Local route required because the request is private, PHI-bearing, or explicitly offline.",
        )

    if request.context_tokens > DEEPSEEK_V4_FLASH_DSPARK.context_tokens:
        return ProviderRouteDecision(
            profile=LOCAL_FIRST_FALLBACK,
            reason="Context exceeds the configured DeepSeek V4 window; segment locally before remote routing.",
        )

    if request.reasoning == "high" and request.budget != "lowest" and not request.latency_sensitive:
        return ProviderRouteDecision(
            profile=DEEPSEEK_V4_PRO_DSPARK,
            reason="High-reasoning public/internal task can use the Pro DSpark escalation profile.",
        )

    if request.requires_json or request.requires_tools or request.latency_sensitive or request.budget in {"lowest", "balanced"}:
        return ProviderRouteDecision(
            profile=DEEPSEEK_V4_FLASH_DSPARK,
            reason="Flash DSpark is the cheap-first long-context route with JSON/tool support.",
        )

    return ProviderRouteDecision(
        profile=DEEPSEEK_V4_FLASH_DSPARK,
        reason="Default public/internal Raven reasoning route.",
    )


def evidence_trace_tags(decision: ProviderRouteDecision) -> tuple[str, ...]:
    """Tags to attach to Raven Evidence Graph traces for provider provenance."""

    return (
        f"provider:{decision.profile.provider}",
        f"model:{decision.profile.model}",
        f"profile:{decision.profile.id}",
    )

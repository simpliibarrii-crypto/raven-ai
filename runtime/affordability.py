"""Affordability tiers for openclinical-ai — equity-first resource policy.

The "affordable for everyone" mandate is more than cheap inference — it's that
the same clinical-quality inference is reachable by a rural critical-access
hospital, a 200-bed LTC home, a regional hospital, and an academic medical
center, without the substrate penalizing smaller institutions.

This module defines tiers, the per-model quantization policy, and the
tier → resource-limit mapping. It is the *policy layer* on top of the
tenant registry: tenants.py owns identity, affordability.py owns policy.

Tiers (designed to map onto Canadian healthcare institution types):

  critical_access_rural   — small hospitals, nursing stations, fly-in only
  ltc_home                — retirement homes, long-term care, group homes
  home_care_agency        — Bayshore, Carefor, VHA, ParaMed, etc.
  regional_hospital       — secondary/tertiary hospitals, regional authorities
  academic_medical_center — UHN, Sunnybrook, Ottawa Hospital, etc.
  biotech_research        — Mila, Vector, NRC, biotech startups
  biotech_sovereign       — sovereign Canadian deployment, fully air-gapped

The DeepSeek V4-Pro + V4-Flash cost equation (per inference):
  V4-Pro:    $0.435/M input + $0.87/M output tokens (published 2026-05-22)
  V4-Flash:  $0.10/M input  + $0.30/M output tokens (estimate)
  DSpark on-prem: $0 marginal API cost after initial setup
  Closed-source baseline: GPT-5.5 ~$10/$30, Opus 4.7 ~$15/$75

Per-tenant cost is reported back to the tenant ONLY — never cross-tenant.
Affordability is for the patient, not for tenant-vs-tenant comparison.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger("openclinical.runtime.affordability")


# --- DeepSeek V4-Pro + V4-Flash pricing (2026-06-28) -----------------------
# Source: https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro
# Updated May 22, 2026 — V4 Pro $0.435/$0.87 per 1M tokens in/out
# V4-Flash pricing is not yet officially published; estimates below are
# in the same order of magnitude as V3-Flash (released 2025).

V4_PRO_INPUT_USD_PER_M = 0.435
V4_PRO_OUTPUT_USD_PER_M = 0.87
V4_FLASH_INPUT_USD_PER_M = 0.10  # estimate — verify before publishing
V4_FLASH_OUTPUT_USD_PER_M = 0.30  # estimate — verify before publishing

# Closed-source baselines (for savings reporting)
GPT55_INPUT_USD_PER_M = 10.0
GPT55_OUTPUT_USD_PER_M = 30.0
OPUS47_INPUT_USD_PER_M = 15.0
OPUS47_OUTPUT_USD_PER_M = 75.0


# --- Tier policy ---------------------------------------------------------


@dataclass
class TierPolicy:
    """Resource + cost policy for an affordability tier.

    Each tier is a bundle of:
    - default model family (v4-pro, v4-flash, dspark, heuristic)
    - default quantization (fp8, fp16, bf16)
    - context + output token limits
    - rate limits
    - escalation permissions (can this tier call V4-Pro for complex cases?)
    - on-prem requirement (DSpark-style fully sovereign deployment)
    """
    tier_id: str
    name: str
    description: str
    default_model_family: str  # v4-pro | v4-flash | dspark | heuristic
    default_quantization: str  # fp8 | fp16 | bf16
    max_context_tokens: int
    max_output_tokens: int
    max_inferences_per_hour: int | None  # None = unlimited
    can_escalate_to_pro: bool
    on_prem_required: bool
    example_institutions: list[str] = field(default_factory=list)
    input_usd_per_m: float = V4_FLASH_INPUT_USD_PER_M
    output_usd_per_m: float = V4_FLASH_OUTPUT_USD_PER_M

    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Estimate USD cost for a single inference at this tier's pricing."""
        input_cost = (input_tokens / 1_000_000) * self.input_usd_per_m
        output_cost = (output_tokens / 1_000_000) * self.output_usd_per_m
        return input_cost + output_cost

    def to_dict(self) -> dict[str, Any]:
        """Public representation — no secrets, safe to expose."""
        return {
            "tier_id": self.tier_id,
            "name": self.name,
            "description": self.description,
            "default_model_family": self.default_model_family,
            "default_quantization": self.default_quantization,
            "max_context_tokens": self.max_context_tokens,
            "max_output_tokens": self.max_output_tokens,
            "max_inferences_per_hour": self.max_inferences_per_hour,
            "can_escalate_to_pro": self.can_escalate_to_pro,
            "on_prem_required": self.on_prem_required,
            "example_institutions": self.example_institutions,
            "input_usd_per_m": self.input_usd_per_m,
            "output_usd_per_m": self.output_usd_per_m,
        }


# Tier table — equity-first: smaller institutions get full feature parity
# just at different resource ceilings. No tier is denied a capability; the
# resource ceiling changes. (See PROJECT-BRIEF.md "Affordability policy".)
ALL_TIERS: dict[str, TierPolicy] = {
    "critical_access_rural": TierPolicy(
        tier_id="critical_access_rural",
        name="Critical Access — Rural",
        description=(
            "Small hospitals, nursing stations, fly-in communities. "
            "Designed for the lowest-bandwidth sovereign deployment: V4-Flash "
            "by default, fp8 quantization, on-prem DSpark option for "
            "fully air-gapped operation."
        ),
        default_model_family="v4-flash",
        default_quantization="fp8",
        max_context_tokens=32_000,
        max_output_tokens=4_000,
        max_inferences_per_hour=2_000,
        can_escalate_to_pro=True,
        on_prem_required=False,
        example_institutions=[
            "Weeneebayko Area Health Authority (WAHA)",
            "North West Company health stations",
            "Remote nursing stations (First Nations)",
        ],
        input_usd_per_m=V4_FLASH_INPUT_USD_PER_M,
        output_usd_per_m=V4_FLASH_OUTPUT_USD_PER_M,
    ),
    "ltc_home": TierPolicy(
        tier_id="ltc_home",
        name="Long-Term Care / Retirement Home",
        description=(
            "200-bed LTC homes, retirement residences, group homes. "
            "Voice-first PSW assistant is the primary use case — short "
            "inferences (shift handoff, vitals concerns) on V4-Flash."
        ),
        default_model_family="v4-flash",
        default_quantization="fp8",
        max_context_tokens=32_000,
        max_output_tokens=2_000,
        max_inferences_per_hour=5_000,
        can_escalate_to_pro=True,
        on_prem_required=False,
        example_institutions=[
            "Garry J. Armstrong Retirement Home (Ottawa)",
            "Perley Health (Ottawa)",
            "Schlegel Villages (Ontario)",
            "Revera (national)",
        ],
        input_usd_per_m=V4_FLASH_INPUT_USD_PER_M,
        output_usd_per_m=V4_FLASH_OUTPUT_USD_PER_M,
    ),
    "home_care_agency": TierPolicy(
        tier_id="home_care_agency",
        name="Home Care Agency",
        description=(
            "PSW visit documentation, family coordination, billing audit "
            "trail. Most inferences are short (one visit summary). "
            "Default tenant tier for new tenants — the most common case."
        ),
        default_model_family="v4-flash",
        default_quantization="fp8",
        max_context_tokens=16_000,
        max_output_tokens=2_000,
        max_inferences_per_hour=10_000,
        can_escalate_to_pro=True,
        on_prem_required=False,
        example_institutions=[
            "Bayshore Home Health (national)",
            "Carefor Health & Community Services",
            "VHA Home HealthCare",
            "SE Health",
            "ParaMed",
        ],
        input_usd_per_m=V4_FLASH_INPUT_USD_PER_M,
        output_usd_per_m=V4_FLASH_OUTPUT_USD_PER_M,
    ),
    "regional_hospital": TierPolicy(
        tier_id="regional_hospital",
        name="Regional Hospital",
        description=(
            "Secondary/tertiary hospitals, regional health authorities. "
            "Drug interaction prediction, clinical reasoning, multi-visit "
            "patient timelines. V4-Pro for complex cases."
        ),
        default_model_family="v4-pro",
        default_quantization="fp16",
        max_context_tokens=128_000,
        max_output_tokens=8_000,
        max_inferences_per_hour=20_000,
        can_escalate_to_pro=True,
        on_prem_required=False,
        example_institutions=[
            "The Ottawa Hospital",
            "CHEO",
            "Health Sciences North (Sudbury)",
            "Regional health authorities (provincial)",
        ],
        input_usd_per_m=V4_PRO_INPUT_USD_PER_M,
        output_usd_per_m=V4_PRO_OUTPUT_USD_PER_M,
    ),
    "academic_medical_center": TierPolicy(
        tier_id="academic_medical_center",
        name="Academic Medical Center",
        description=(
            "UHN, Sunnybrook, large teaching hospitals. Million-token "
            "context for full patient histories, research workloads, "
            "variant-impact prediction, clinical trial matching."
        ),
        default_model_family="v4-pro",
        default_quantization="fp16",
        max_context_tokens=1_000_000,
        max_output_tokens=16_000,
        max_inferences_per_hour=50_000,
        can_escalate_to_pro=True,
        on_prem_required=False,
        example_institutions=[
            "University Health Network (UHN)",
            "Sunnybrook Health Sciences Centre",
            "Mount Sinai Hospital (Toronto)",
            "Vancouver General Hospital",
        ],
        input_usd_per_m=V4_PRO_INPUT_USD_PER_M,
        output_usd_per_m=V4_PRO_OUTPUT_USD_PER_M,
    ),
    "biotech_research": TierPolicy(
        tier_id="biotech_research",
        name="Biotech Research Lab",
        description=(
            "Protein design, RNA structure, generative biology. V4-Pro "
            "for sequence reasoning + DSpark on-prem option for fully "
            "sovereign weights. Biosecurity screening mandatory."
        ),
        default_model_family="v4-pro",
        default_quantization="fp16",
        max_context_tokens=1_000_000,
        max_output_tokens=16_000,
        max_inferences_per_hour=50_000,
        can_escalate_to_pro=True,
        on_prem_required=False,
        example_institutions=[
            "Mila (Montréal)",
            "Vector Institute (Toronto)",
            "NRC",
            "AbCellera (Vancouver)",
        ],
        input_usd_per_m=V4_PRO_INPUT_USD_PER_M,
        output_usd_per_m=V4_PRO_OUTPUT_USD_PER_M,
    ),
    "biotech_sovereign": TierPolicy(
        tier_id="biotech_sovereign",
        name="Sovereign Biotech (DSpark On-Prem)",
        description=(
            "Fully air-gapped Canadian deployment. DSpark inference "
            "framework runs on local hardware; no data leaves the "
            "deployment. $0 marginal API cost after setup. "
            "Context length bounded by local hardware, not by tier policy."
        ),
        default_model_family="dspark",
        default_quantization="fp16",
        max_context_tokens=1_000_000,
        max_output_tokens=16_000,
        max_inferences_per_hour=None,  # unlimited, hardware-bounded
        can_escalate_to_pro=False,  # no escalation — sovereign = sovereign
        on_prem_required=True,
        example_institutions=[
            "Canadian sovereign AI deployments",
            "Government research labs",
            "Air-gapped biotech facilities",
        ],
        input_usd_per_m=0.0,
        output_usd_per_m=0.0,
    ),
}


DEFAULT_TIER = "home_care_agency"


def get_tier(tier_id: str) -> TierPolicy:
    """Resolve a tier ID to its policy. Defaults to home_care_agency."""
    return ALL_TIERS.get(tier_id) or ALL_TIERS[DEFAULT_TIER]


def list_tiers() -> list[dict[str, Any]]:
    """List all tiers (public, no secrets)."""
    return [t.to_dict() for t in ALL_TIERS.values()]


# --- Per-model quantization policy -----------------------------------------
# Quantization is a per-model-class decision, not a per-tenant one.
# Reasoning: a regulatory body will ask "is the output deterministic enough
# for the clinical decision being made?" — that's a property of the model's
# output class, not the tenant's wallet.

CLINICAL_DECISION_CLASSES = {
    "drug-interaction-prediction",
    "variant-impact-prediction",
    "adverse-event-detection",
    "fall-risk-assessment",
}


def default_quantization_for(model_id: str, tier_id: str) -> str:
    """Pick default quantization for a model + tier.

    Clinical-decision-class models always default to fp16 (deterministic-enough).
    Other models respect the tier default (fp8 for resource-constrained tiers).
    """
    # Clinical-decision models: always fp16 regardless of tier
    base = model_id.split(":")[0] if ":" in model_id else model_id
    if base in CLINICAL_DECISION_CLASSES:
        return "fp16"

    tier = get_tier(tier_id)
    return tier.default_quantization


def estimate_cost(
    tier_id: str,
    input_tokens: int,
    output_tokens: int,
) -> dict[str, float]:
    """Estimate cost for a single inference at a given tier.

    Returns cost at the tier's pricing PLUS savings vs GPT-5.5 and Opus 4.7.
    """
    tier = get_tier(tier_id)
    tier_cost = tier.estimate_cost(input_tokens, output_tokens)

    gpt55_cost = (
        (input_tokens / 1_000_000) * GPT55_INPUT_USD_PER_M
        + (output_tokens / 1_000_000) * GPT55_OUTPUT_USD_PER_M
    )
    opus47_cost = (
        (input_tokens / 1_000_000) * OPUS47_INPUT_USD_PER_M
        + (output_tokens / 1_000_000) * OPUS47_OUTPUT_USD_PER_M
    )

    return {
        "tier_cost_usd": round(tier_cost, 8),
        "savings_vs_gpt55_usd": round(gpt55_cost - tier_cost, 8),
        "savings_vs_opus47_usd": round(opus47_cost - tier_cost, 8),
        "savings_multiplier_vs_gpt55": (
            round(gpt55_cost / tier_cost, 1) if tier_cost > 0 else float("inf")
        ),
        "savings_multiplier_vs_opus47": (
            round(opus47_cost / tier_cost, 1) if tier_cost > 0 else float("inf")
        ),
    }


def estimate_flops(
    activated_params_b: float,
    input_tokens: int,
    output_tokens: int,
) -> float:
    """Estimate inference FLOPs (single-token FLOPs × tokens).

    Reference: DeepSeek V4-Pro publishes 49B activated params. Single-token
    FLOPs ≈ 2 × activated_params (matmul forward). For the substrate we
    expose this as an estimate for cost / energy reporting.
    """
    single_token_flops = 2 * activated_params_b * 1e9
    total_tokens = input_tokens + output_tokens
    return single_token_flops * total_tokens
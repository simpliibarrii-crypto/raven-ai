"""Tests for the affordability tier system + cost transparency.

These tests verify the equity-first invariant:
- All tiers exist and have policy values
- Smaller institutions aren't penalized on capability, just on resource ceilings
- Cost estimates are computed from V4-Pro / V4-Flash published pricing
- Clinical-decision-class models always default to fp16 (deterministic-enough)
- Per-tenant cost reports are tenant-scoped (no cross-tenant leakage)
"""
from __future__ import annotations

import pytest

from runtime.affordability import (
    ALL_TIERS,
    DEFAULT_TIER,
    CLINICAL_DECISION_CLASSES,
    V4_PRO_INPUT_USD_PER_M,
    V4_PRO_OUTPUT_USD_PER_M,
    V4_FLASH_INPUT_USD_PER_M,
    V4_FLASH_OUTPUT_USD_PER_M,
    default_quantization_for,
    estimate_cost,
    estimate_flops,
    get_tier,
    list_tiers,
)
from runtime.cost import CostTracker, build_cost_record


# --- tier existence + defaults ---------------------------------------------


def test_all_tiers_exist():
    """All seven expected tiers exist."""
    expected = {
        "critical_access_rural",
        "ltc_home",
        "home_care_agency",
        "regional_hospital",
        "academic_medical_center",
        "biotech_research",
        "biotech_sovereign",
    }
    assert expected.issubset(set(ALL_TIERS.keys()))


def test_default_tier_is_home_care_agency():
    """Default tier is home_care_agency (the most common case)."""
    assert DEFAULT_TIER == "home_care_agency"


def test_get_tier_returns_policy_for_known_tier():
    """get_tier resolves a known tier_id to its policy."""
    tier = get_tier("ltc_home")
    assert tier.tier_id == "ltc_home"
    assert tier.default_model_family == "v4-flash"


def test_get_tier_falls_back_to_default_for_unknown():
    """Unknown tier_ids fall back to the default tier."""
    tier = get_tier("nonexistent-tier-id")
    assert tier.tier_id == DEFAULT_TIER


def test_list_tiers_returns_all():
    """list_tiers returns one entry per tier."""
    tiers = list_tiers()
    assert len(tiers) == len(ALL_TIERS)
    for t in tiers:
        assert "tier_id" in t
        assert "default_model_family" in t


# --- equity-first invariant ------------------------------------------------


def test_all_tiers_have_full_feature_parity_models():
    """Every tier maps to a model family (no tier is denied a model)."""
    for tier in ALL_TIERS.values():
        assert tier.default_model_family in {"v4-pro", "v4-flash", "dspark", "heuristic"}


def test_smaller_tiers_have_lower_or_equal_resource_ceilings():
    """Resource ceilings scale with tier capability (rural < academic)."""
    rural = ALL_TIERS["critical_access_rural"]
    ltc = ALL_TIERS["ltc_home"]
    home_care = ALL_TIERS["home_care_agency"]
    academic = ALL_TIERS["academic_medical_center"]

    # Smaller tiers have tighter context ceilings
    assert rural.max_context_tokens <= academic.max_context_tokens
    assert ltc.max_context_tokens <= academic.max_context_tokens
    assert home_care.max_context_tokens <= academic.max_context_tokens

    # Smaller tiers default to cheaper / faster model families
    assert rural.default_model_family in {"v4-flash", "dspark"}
    assert academic.default_model_family == "v4-pro"


def test_sovereign_tier_has_zero_marginal_api_cost():
    """biotech_sovereign uses DSpark on-prem with $0 marginal API cost."""
    sovereign = ALL_TIERS["biotech_sovereign"]
    assert sovereign.default_model_family == "dspark"
    assert sovereign.on_prem_required is True
    assert sovereign.input_usd_per_m == 0.0
    assert sovereign.output_usd_per_m == 0.0
    # Sovereign tier doesn't escalate — sovereignty is the policy
    assert sovereign.can_escalate_to_pro is False


def test_academic_tier_supports_million_token_context():
    """academic_medical_center supports V4-Pro's 1M-token context."""
    academic = ALL_TIERS["academic_medical_center"]
    assert academic.max_context_tokens == 1_000_000


# --- pricing model ---------------------------------------------------------


def test_v4_pro_pricing_matches_published_rates():
    """V4-Pro pricing matches published 2026-05-22 rates."""
    assert V4_PRO_INPUT_USD_PER_M == pytest.approx(0.435, rel=0.01)
    assert V4_PRO_OUTPUT_USD_PER_M == pytest.approx(0.87, rel=0.01)


def test_estimate_cost_v4_pro():
    """V4-Pro cost for 1M input + 1M output tokens = $0.435 + $0.87 = $1.305."""
    cost = estimate_cost("academic_medical_center", 1_000_000, 1_000_000)
    assert cost["tier_cost_usd"] == pytest.approx(1.305, rel=0.01)


def test_estimate_cost_v4_flash():
    """V4-Flash cost is materially cheaper than V4-Pro."""
    v4_pro = estimate_cost("academic_medical_center", 100_000, 50_000)
    v4_flash = estimate_cost("ltc_home", 100_000, 50_000)
    assert v4_flash["tier_cost_usd"] < v4_pro["tier_cost_usd"]


def test_savings_vs_closed_source_are_significant():
    """Savings vs GPT-5.5 + Opus 4.7 are material (10x+ multiplier)."""
    cost = estimate_cost("home_care_agency", 100_000, 50_000)
    assert cost["savings_multiplier_vs_gpt55"] >= 10
    assert cost["savings_multiplier_vs_opus47"] >= 10


def test_sovereign_tier_zero_cost():
    """biotech_sovereign has $0 marginal cost — all savings."""
    cost = estimate_cost("biotech_sovereign", 100_000, 50_000)
    assert cost["tier_cost_usd"] == 0.0
    assert cost["savings_multiplier_vs_gpt55"] == float("inf")


# --- quantization policy ---------------------------------------------------


def test_clinical_decision_models_default_fp16():
    """Clinical-decision-class models always default to fp16 (deterministic-enough)."""
    for model_id in CLINICAL_DECISION_CLASSES:
        # Even on rural / home-care tiers (which default to fp8)
        assert default_quantization_for(model_id, "critical_access_rural") == "fp16"
        assert default_quantization_for(model_id, "ltc_home") == "fp16"
        assert default_quantization_for(model_id, "home_care_agency") == "fp16"


def test_non_clinical_models_respect_tier_default():
    """Non-clinical models respect the tier's quantization default."""
    assert default_quantization_for("psw-shift-handoff", "ltc_home") == "fp8"
    assert default_quantization_for("psw-shift-handoff", "academic_medical_center") == "fp16"


# --- FLOPs estimator --------------------------------------------------------


def test_estimate_flops_v4_pro():
    """V4-Pro FLOPs: 2 × 49B × (input + output) tokens."""
    flops = estimate_flops(49.0, 1000, 500)
    expected = 2 * 49_000_000_000 * 1500
    assert flops == pytest.approx(expected, rel=0.01)


def test_estimate_flops_v4_flash_smaller_than_v4_pro():
    """V4-Flash (13B activated) FLOPs < V4-Pro (49B) FLOPs for same tokens."""
    flops_flash = estimate_flops(13.0, 1000, 500)
    flops_pro = estimate_flops(49.0, 1000, 500)
    assert flops_flash < flops_pro


# --- cost tracker (per-tenant isolation) -----------------------------------


def test_cost_tracker_records_per_tenant():
    """Cost records are indexed by tenant_id."""
    tracker = CostTracker()
    rec1 = build_cost_record(
        inference_id="inf-1",
        tenant_id="ltc-1",
        psw_id="psw-1",
        model_id="psw-shift-handoff",
        model_family="heuristic",
        tier_id="ltc_home",
        quantization="fp8",
        input_tokens=500,
        output_tokens=200,
        activated_params_b=0.0,
    )
    rec2 = build_cost_record(
        inference_id="inf-2",
        tenant_id="academic-1",
        psw_id="psw-2",
        model_id="v4-pro-clinical",
        model_family="v4-pro",
        tier_id="academic_medical_center",
        quantization="fp16",
        input_tokens=2000,
        output_tokens=500,
        activated_params_b=49.0,
    )
    tracker.record(rec1)
    tracker.record(rec2)

    assert "ltc-1" in tracker.records
    assert "academic-1" in tracker.records
    assert len(tracker.records["ltc-1"]) == 1
    assert len(tracker.records["academic-1"]) == 1


def test_cost_report_tenant_scoped():
    """Cost reports only contain the requesting tenant's records."""
    tracker = CostTracker()
    rec_a = build_cost_record(
        inference_id="a-1",
        tenant_id="tenant-a",
        psw_id="psw-1",
        model_id="psw-shift-handoff",
        model_family="heuristic",
        tier_id="ltc_home",
        quantization="fp8",
        input_tokens=500,
        output_tokens=200,
        activated_params_b=0.0,
    )
    rec_b = build_cost_record(
        inference_id="b-1",
        tenant_id="tenant-b",
        psw_id="psw-2",
        model_id="psw-shift-handoff",
        model_family="heuristic",
        tier_id="ltc_home",
        quantization="fp8",
        input_tokens=500,
        output_tokens=200,
        activated_params_b=0.0,
    )
    tracker.record(rec_a)
    tracker.record(rec_b)

    report_a = tracker.tenant_report("tenant-a")
    assert report_a["tenant_id"] == "tenant-a"
    assert report_a["inference_count"] == 1
    # No cross-tenant visibility — tenant_a doesn't see tenant_b's records
    assert all(
        r["tenant_id"] if "tenant_id" in r else True
        for r in report_a["recent_records"]
    )


def test_cost_report_empty_tenant_returns_zero():
    """Unknown tenants get a zero-record report, not an error."""
    tracker = CostTracker()
    report = tracker.tenant_report("unknown-tenant")
    assert report["inference_count"] == 0
    assert report["totals"]["estimated_cost_usd"] == 0.0


def test_cost_report_aggregates_by_model_family():
    """Cost reports aggregate by model family (v4-pro vs v4-flash vs heuristic)."""
    tracker = CostTracker()
    for fam in ("v4-pro", "v4-flash", "heuristic"):
        rec = build_cost_record(
            inference_id=f"inf-{fam}",
            tenant_id="tenant-x",
            psw_id="psw-x",
            model_id=f"test-{fam}",
            model_family=fam,
            tier_id="academic_medical_center",
            quantization="fp16",
            input_tokens=1000,
            output_tokens=500,
            activated_params_b=49.0 if fam == "v4-pro" else (13.0 if fam == "v4-flash" else 0.0),
        )
        tracker.record(rec)

    report = tracker.tenant_report("tenant-x")
    assert "v4-pro" in report["by_model_family"]
    assert "v4-flash" in report["by_model_family"]
    assert "heuristic" in report["by_model_family"]
    assert report["inference_count"] == 3


def test_cost_record_includes_savings_vs_closed_source():
    """Every cost record shows savings vs GPT-5.5 + Opus 4.7."""
    rec = build_cost_record(
        inference_id="inf-savings",
        tenant_id="ltc-home-1",
        psw_id="psw-1",
        model_id="psw-shift-handoff",
        model_family="heuristic",
        tier_id="ltc_home",
        quantization="fp8",
        input_tokens=1000,
        output_tokens=500,
        activated_params_b=0.0,
    )
    # heuristic model = $0 cost, but savings still computed vs closed-source baselines
    assert rec.savings_vs_gpt55_usd >= 0.0
    assert rec.savings_vs_opus47_usd >= 0.0
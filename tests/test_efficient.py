"""Tests for efficient inference interface (DeepSeek V4-Pro / DSpark patterns).

These tests verify the SEAMS, not fake-routed inference. The MVP heuristic
adapters return all experts (no real routing). Real adapters plug in here
without changing the substrate.
"""
from __future__ import annotations

import pytest

from runtime.efficient import (
    CompressedContext,
    ContextCompressor,
    ExpertRoute,
    ExpertRouter,
    TieredModelAdapter,
    TieredModelSpec,
    default_compressor,
    default_router,
    DEFAULT_MEDICAL_EXPERTS,
)


# --- expert routing (MoE seam) ---------------------------------------------


def test_default_router_has_medical_specialty_experts():
    """Default router is configured with medical-specialty experts."""
    router = default_router()
    assert len(router.experts) == len(DEFAULT_MEDICAL_EXPERTS)
    specialties = {e.specialty for e in router.experts}
    assert "Pharmacology" in specialties
    assert "Geriatric medicine" in specialties
    assert "Mental health" in specialties


def test_router_returns_all_experts_mvp():
    """MVP heuristic: returns all experts (no real selection yet)."""
    router = default_router()
    selected = router.route({"input": "patient with chest pain"})
    assert len(selected) == len(DEFAULT_MEDICAL_EXPERTS)


def test_router_activated_params_sums_experts():
    """Activated params sums across selected experts."""
    experts = [
        ExpertRoute("a", "test", ["x"], estimated_params_b=5.0),
        ExpertRoute("b", "test", ["y"], estimated_params_b=3.0),
    ]
    router = ExpertRouter(experts)
    selected = router.route({})
    assert router.activated_params_b(selected) == 8.0


def test_empty_router_returns_no_experts():
    """Router with no experts returns no experts."""
    router = ExpertRouter([])
    assert router.route({}) == []


# --- context compression (CSA + HCA seam) ---------------------------------


def test_compressor_no_op_for_short_context():
    """Short context passes through unchanged."""
    compressor = default_compressor()
    result = compressor.compress("Patient is alert.", max_tokens=1000)
    assert result.original_tokens == 3
    assert result.compressed_tokens == 3
    assert result.compression_ratio == 1.0
    assert result.method == "csa"


def test_compressor_compresses_long_context():
    """Long context compresses to fit max_tokens."""
    compressor = default_compressor()
    long_context = " ".join(["word"] * 2500)  # 2500 word tokens
    result = compressor.compress(long_context, max_tokens=100)
    assert result.original_tokens == 2500
    assert result.compressed_tokens <= 100
    assert result.compression_ratio < 1.0


def test_compressor_preserves_clinical_anchors():
    """Compression preserves lines with clinical keywords (diagnoses, allergies, etc.)."""
    compressor = default_compressor()
    long_context = (
        " ".join(["Routine"] * 100)
        + " DIAGNOSIS: atrial fibrillation. "
        + "ALLERGY: penicillin. "
        + "MEDICATION: warfarin 5mg daily. "
        + " ".join(["Routine"] * 100)
    )
    result = compressor.compress(long_context, max_tokens=200)
    # Anchors should include the diagnosis / allergy / medication lines
    assert any("DIAGNOSIS" in a for a in result.semantic_anchors)
    assert any("ALLERGY" in a for a in result.semantic_anchors)
    assert any("MEDICATION" in a for a in result.semantic_anchors)


def test_compressor_method_hca_for_aggressive_compression():
    """Method is 'hca' for aggressive compression (>10x ratio)."""
    compressor = default_compressor()
    long_context = " ".join(["word"] * 10000)
    result = compressor.compress(long_context, max_tokens=100)
    assert result.method == "hca"


def test_compressor_method_csa_for_moderate_compression():
    """Method is 'csa' for moderate compression (10-50% ratio)."""
    compressor = default_compressor()
    long_context = " ".join(["word"] * 1000)
    result = compressor.compress(long_context, max_tokens=300)
    assert result.method == "csa"


def test_compressor_handles_empty_context():
    """Empty context returns a zero-token CompressedContext."""
    compressor = default_compressor()
    result = compressor.compress("", max_tokens=1000)
    assert result.original_tokens == 0
    assert result.compressed_tokens == 0


def test_compressed_context_to_dict():
    """CompressedContext serializes via to_dict."""
    cc = CompressedContext(
        original_tokens=1000,
        compressed_tokens=200,
        compression_ratio=0.2,
        method="csa",
        semantic_anchors=["DIAGNOSIS: CHF"],
    )
    d = cc.to_dict()
    assert d["original_tokens"] == 1000
    assert d["compressed_tokens"] == 200
    assert d["compression_ratio"] == 0.2
    assert d["method"] == "csa"
    assert d["semantic_anchors"] == ["DIAGNOSIS: CHF"]


# --- tiered model adapter ------------------------------------------------


def test_tiered_model_adapter_resolves_spec_by_tier():
    """Adapter maps tier_id to its TieredModelSpec."""
    specs = [
        TieredModelSpec("m", "v4-pro", 49.0, "fp16", 1_000_000, 0.435, 0.87),
        TieredModelSpec("m", "v4-flash", 13.0, "fp8", 32_000, 0.10, 0.30),
    ]
    adapter = TieredModelAdapter(specs)
    pro = adapter.spec_for("v4-pro")
    flash = adapter.spec_for("v4-flash")
    assert pro.activated_params_b == 49.0
    assert flash.activated_params_b == 13.0


def test_tiered_model_adapter_returns_none_for_unknown_tier():
    """Unknown tier returns None (no implicit fallback)."""
    specs = [TieredModelSpec("m", "v4-pro", 49.0, "fp16", 1_000_000, 0.435, 0.87)]
    adapter = TieredModelAdapter(specs)
    assert adapter.spec_for("unknown-tier") is None


def test_tiered_model_adapter_base_run_raises():
    """Base class run() raises — real adapters must override."""
    adapter = TieredModelAdapter([])
    import asyncio
    with pytest.raises(NotImplementedError):
        asyncio.run(adapter.run({}))
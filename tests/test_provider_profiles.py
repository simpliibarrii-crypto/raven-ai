from __future__ import annotations

import pytest

from runtime.provider_profiles import (
    CHEAP_REMOTE_LANE,
    DEEPSEEK_V4_FLASH_DSPARK,
    LOCAL_FIRST_FALLBACK,
    STRONG_REMOTE_LANE,
    ProviderRouteRequest,
    evidence_trace_tags,
    get_provider_profile,
    select_provider,
)


def test_cheap_remote_lane_is_default_draft_route():
    decision = select_provider(
        ProviderRouteRequest(
            task="summarize public research notes",
            context_tokens=220_000,
            reasoning="medium",
            budget="lowest",
            requires_json=True,
        )
    )

    assert decision.profile == CHEAP_REMOTE_LANE
    assert decision.profile.provider == "remote-generic"
    assert decision.profile.supports_json is True
    assert decision.profile.supports_tools is True
    assert "Cheap remote lane" in decision.reason


def test_strong_remote_lane_is_high_reasoning_escalation():
    decision = select_provider(
        ProviderRouteRequest(
            task="plan a multi-agent biology workflow",
            context_tokens=400_000,
            reasoning="high",
            budget="premium",
            latency_sensitive=False,
        )
    )

    assert decision.profile == STRONG_REMOTE_LANE
    assert "strong escalation lane" in decision.reason


def test_private_or_phi_work_routes_local_first():
    for sensitivity in ("private", "phi"):
        decision = select_provider(
            ProviderRouteRequest(
                task="clinical handoff summary",
                sensitivity=sensitivity,
                reasoning="high",
                budget="premium",
            )
        )

        assert decision.profile == LOCAL_FIRST_FALLBACK
        assert "Local route required" in decision.reason


def test_context_overflow_requires_local_segmentation():
    decision = select_provider(
        ProviderRouteRequest(
            task="oversized corpus synthesis",
            context_tokens=1_000_001,
            reasoning="medium",
        )
    )

    assert decision.profile == LOCAL_FIRST_FALLBACK
    assert "segment locally" in decision.reason


def test_evidence_trace_tags_capture_vendor_neutral_lane():
    decision = select_provider(ProviderRouteRequest(task="public literature synthesis"))

    assert evidence_trace_tags(decision) == (
        "provider:remote-generic",
        "model:cheap-long-context-or-fast-reasoning",
        "profile:cheap-remote-lane",
    )


def test_deepseek_profile_is_reference_not_default():
    profile = get_provider_profile("deepseek-v4-flash-dspark")

    assert profile == DEEPSEEK_V4_FLASH_DSPARK
    assert profile.provider == "deepseek"
    assert "Research reference only" in profile.notes


def test_get_provider_profile_rejects_unknown_ids():
    assert get_provider_profile("cheap-remote-lane") == CHEAP_REMOTE_LANE
    with pytest.raises(KeyError):
        get_provider_profile("missing")

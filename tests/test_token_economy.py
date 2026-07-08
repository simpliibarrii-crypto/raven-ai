from __future__ import annotations

from runtime.token_economy import (
    TokenEconomyRequest,
    VerificationSpan,
    estimate_survival_probability,
    plan_token_economy,
    schedule_verification,
)


def test_cache_hit_reuses_context_and_keeps_thinking_low():
    plan = plan_token_economy(
        TokenEconomyRequest(
            task="answer a repeated product question",
            complexity="simple",
            risk="low",
            estimated_context_tokens=20_000,
            estimated_output_tokens=700,
            cache_hit_ratio=0.85,
            draft_confidence=0.92,
            evidence_coverage=0.8,
        )
    )

    assert plan.draft_lane == "cache"
    assert plan.thinking_level == "low"
    assert plan.context_budget == 3_000
    assert plan.estimated_saved_context_tokens == 17_000
    assert plan.should_escalate is False
    assert "reuse cached summaries before adding raw context" in plan.actions


def test_private_clinical_work_stays_local_even_when_hard():
    plan = plan_token_economy(
        TokenEconomyRequest(
            task="summarize private clinical handoff",
            complexity="hard",
            risk="high",
            privacy="phi",
            estimated_context_tokens=80_000,
            estimated_output_tokens=2_500,
            draft_confidence=0.4,
            evidence_coverage=0.6,
        )
    )

    assert plan.draft_lane == "local-large"
    assert plan.thinking_level == "high"
    assert plan.context_budget == 24_000
    assert plan.should_escalate is False
    assert "keep private context on local or institution-approved models" in plan.actions


def test_research_task_escalates_only_after_cheap_draft_fails_floor():
    plan = plan_token_economy(
        TokenEconomyRequest(
            task="synthesize multi-paper biology architecture",
            complexity="research",
            risk="medium",
            estimated_context_tokens=180_000,
            estimated_output_tokens=6_000,
            draft_confidence=0.35,
            evidence_coverage=0.45,
            requires_exact_citations=True,
        )
    )

    assert plan.draft_lane == "remote-cheap"
    assert plan.thinking_level == "max"
    assert plan.context_budget == 96_000
    assert plan.max_output_tokens == 4_096
    assert plan.should_escalate is True
    assert "escalate only after cheap draft fails confidence floor" in plan.actions


def test_survival_probability_rewards_confidence_and_evidence():
    weak = estimate_survival_probability(
        TokenEconomyRequest(task="weak draft", draft_confidence=0.3, evidence_coverage=0.2, risk="high")
    )
    strong = estimate_survival_probability(
        TokenEconomyRequest(task="strong draft", draft_confidence=0.9, evidence_coverage=0.9, risk="low")
    )

    assert weak < 0.3
    assert strong > 0.8


def test_verification_schedule_prioritizes_risk_and_uncertainty_under_load():
    spans = [
        VerificationSpan("stable low-risk citation", confidence=0.94, risk="low", evidence_coverage=0.9),
        VerificationSpan("uncertain claim", confidence=0.42, risk="medium", evidence_coverage=0.5),
        VerificationSpan("critical clinical claim", confidence=0.86, risk="critical", evidence_coverage=0.75),
        VerificationSpan("weak high-risk claim", confidence=0.2, risk="high", evidence_coverage=0.2),
    ]

    schedule = schedule_verification(spans, system_load=0.9)
    labels = [span.label for span in schedule.spans_to_verify]

    assert labels[0] == "critical clinical claim"
    assert "weak high-risk claim" in labels
    assert "stable low-risk citation" in [span.label for span in schedule.skipped_spans]
    assert schedule.token_budget == len(schedule.spans_to_verify) * 96

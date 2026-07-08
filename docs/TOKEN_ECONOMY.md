# Raven Token Economy

Raven Token Economy applies the useful DSpark principle to Raven without depending on DeepSeek directly.

The product lesson is simple: do cheap work first, verify only what needs verification, and escalate only when uncertainty, risk, or complexity demands it.

## DSpark Principle Applied To Raven

| DSpark idea | Raven product behavior |
|---|---|
| Draft before verify | Generate a cheap draft from cache, tools, local-small models, or a cheap remote lane before using stronger reasoning. |
| Confidence-scheduled verification | Verify low-confidence, high-risk, weak-evidence claims first instead of rechecking every token or every document. |
| Load-aware verification | Under load, keep critical/high-risk verification but skip stable low-risk spans. |
| Semi-autoregressive drafting | Let fast local/tool passes sketch structure, then let stronger agents verify spans and evidence edges. |
| Preserve output quality | Evidence Graph keeps provenance, confidence, risk, provider/profile tags, and claim-level review records. |

## Runtime API

The policy engine lives in `runtime/token_economy.py` and is model-agnostic.

```python
from runtime.token_economy import TokenEconomyRequest, plan_token_economy

plan = plan_token_economy(
    TokenEconomyRequest(
        task="public literature synthesis",
        complexity="research",
        risk="medium",
        estimated_context_tokens=180_000,
        cache_hit_ratio=0.35,
        draft_confidence=0.45,
        evidence_coverage=0.55,
        requires_exact_citations=True,
    )
)

print(plan.draft_lane)
print(plan.actions)
```

## Product Rules

1. Cache summaries and prior run traces before adding raw context.
2. Retrieve narrow evidence slices instead of dumping whole files into prompts.
3. Draft first with the cheapest acceptable lane: cache, deterministic tool, local-small, local-large, remote-cheap, then remote-strong.
4. Estimate whether the draft will survive verification using confidence, evidence coverage, risk, and complexity.
5. Verify claims by priority, not by habit: critical first, then high-risk/low-confidence/weak-evidence spans.
6. Escalate only after the cheap draft fails the confidence floor.
7. Keep PHI and private data on local or institution-approved models.
8. Attach token-economy decisions to Raven Evidence Graph traces for audit and cost review.

## Thinking Levels

| Level | Use when |
|---|---|
| `off` | Trivial, low-risk, cached/tool answer. |
| `low` | Simple low-risk drafting or formatting. |
| `medium` | Standard agent work with moderate uncertainty. |
| `high` | Hard, high-risk, citation-heavy, or private clinical review. |
| `max` | Research synthesis, critical work, or tasks requiring careful multi-step verification. |

## Verification Scheduling

`VerificationSpan` lets Raven verify only the claims that need attention.

```python
from runtime.token_economy import VerificationSpan, schedule_verification

schedule = schedule_verification([
    VerificationSpan("stable citation", confidence=0.94, risk="low", evidence_coverage=0.9),
    VerificationSpan("weak claim", confidence=0.2, risk="high", evidence_coverage=0.2),
    VerificationSpan("critical clinical claim", confidence=0.86, risk="critical", evidence_coverage=0.75),
])
```

Critical spans always stay in the verification queue. High-load mode can skip stable low-risk spans, but not critical work.

## Ecosystem Fit

| App | Token economy role |
|---|---|
| Raven AI | Owns the policy engine and attaches token-economy metadata to Evidence Graph traces. |
| OpenClinical AI | Uses local-first verification and never sends PHI to remote lanes by default. |
| Home for AI | Shows users why an answer used cache, tools, local models, or escalation. |
| Hermes Edge | Provides the local-small/local-large lanes and edge benchmarks for real device savings. |

## What This Is Not

This is not a DeepSeek dependency. DeepSeek DSpark is the research inspiration. Raven Token Economy is the product feature.

It does not claim DSpark speedups for Raven until Raven workflows are benchmarked. It creates the policy surface needed to measure those savings honestly.

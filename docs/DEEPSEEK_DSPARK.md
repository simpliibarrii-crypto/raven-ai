# DeepSeek DSpark Research Note

This document records what Raven learns from DeepSeek DSpark. It is not a requirement to use DeepSeek directly.

The product feature is [Raven Token Economy](TOKEN_ECONOMY.md): a model-agnostic policy for drafting cheaply, verifying adaptively, reusing cache, narrowing context, and escalating only when needed.

## What Was Researched

| Area | Finding | Source |
|---|---|---|
| API models | DeepSeek exposes `deepseek-v4-flash` and `deepseek-v4-pro` from `https://api.deepseek.com`, with OpenAI and Anthropic-compatible APIs. | https://api-docs.deepseek.com/quick_start/pricing |
| Long context | Official DeepSeek API docs list a 1M context length and maximum 384K output for V4 Flash and Pro. | https://api-docs.deepseek.com/quick_start/pricing |
| JSON and tools | Both V4 Flash and Pro list JSON output and tool-call support. | https://api-docs.deepseek.com/quick_start/pricing |
| V4 positioning | DeepSeek describes V4 Flash as smaller, faster, and cost-effective; V4 Pro as the stronger reasoning/agentic model. | https://api-docs.deepseek.com/news/news260424 |
| DSpark meaning | DSpark variants are not new base models; the Hugging Face card says they are the same checkpoint with an additional speculative decoding module attached. | https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash-DSpark |
| Research claim | The DSpark paper describes confidence-scheduled speculative decoding and reports 60-85 percent per-user generation speedups over the MTP-1 baseline in DeepSeek-V4 serving. | https://arxiv.org/abs/2607.05147 |

## Principle To Copy

Raven should copy the control pattern, not the vendor dependency:

1. **Draft cheaply first.** Use cache, deterministic tools, local-small models, or cheap model lanes before heavy reasoning.
2. **Estimate draft survival.** Use confidence, evidence coverage, risk, complexity, and citation requirements to decide whether a cheap draft is likely to pass verification.
3. **Verify selectively.** Verify critical, high-risk, low-confidence, or weak-evidence spans instead of rechecking everything.
4. **Respond to load.** Under high system load, preserve critical verification but skip stable low-risk spans.
5. **Escalate late.** Use stronger models only after the cheap draft fails the confidence floor.
6. **Keep provenance.** Attach the token-economy decision to Raven Evidence Graph traces so users can audit why the system spent tokens.

## Raven Implementation

`runtime/token_economy.py` implements the product policy.

```python
from runtime.token_economy import TokenEconomyRequest, plan_token_economy

plan = plan_token_economy(
    TokenEconomyRequest(
        task="summarize public literature",
        complexity="research",
        estimated_context_tokens=180_000,
        cache_hit_ratio=0.35,
        draft_confidence=0.45,
        evidence_coverage=0.55,
        requires_exact_citations=True,
    )
)
```

`runtime/provider_profiles.py` remains a separate provider-capability registry. It can describe DeepSeek, OpenRouter, Qwen, local models, or future providers, but it is not the heart of the DSpark-inspired product feature.

## Ecosystem Fit

| App | Token-saving role |
|---|---|
| Raven AI | Owns token economy, confidence scheduling, provider tags, and Evidence Graph traces. |
| OpenClinical AI | Keeps PHI local, verifies critical spans, and avoids remote escalation by default. |
| Home for AI | Shows users when answers came from cache, tools, local lanes, or escalation. |
| Hermes Edge | Supplies local-small/local-large draft lanes and device benchmarks. |

## Implementation Notes

- Keep direct provider API keys out of source control.
- Do not claim DSpark speedups for Raven until Raven workflows are benchmarked.
- Use Evidence Graph to record token-economy decisions, draft lane, confidence floor, and verification spans.
- Redact and slice context before any remote model call.
- Treat DeepSeek DSpark as research inspiration and an optional provider profile, not as Raven's default product identity.

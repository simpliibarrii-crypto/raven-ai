# DeepSeek DSpark Integration

Raven should treat DeepSeek DSpark as a fast remote inference profile for public or approved internal work, not as a replacement for local privacy controls or Evidence Graph provenance.

## What Was Researched

| Area | Finding | Source |
|---|---|---|
| API models | DeepSeek exposes `deepseek-v4-flash` and `deepseek-v4-pro` from `https://api.deepseek.com`, with OpenAI and Anthropic-compatible APIs. | https://api-docs.deepseek.com/quick_start/pricing |
| Long context | Official DeepSeek API docs list a 1M context length and maximum 384K output for V4 Flash and Pro. | https://api-docs.deepseek.com/quick_start/pricing |
| JSON and tools | Both V4 Flash and Pro list JSON output and tool-call support. | https://api-docs.deepseek.com/quick_start/pricing |
| V4 positioning | DeepSeek describes V4 Flash as smaller, faster, and cost-effective; V4 Pro as the stronger reasoning/agentic model. | https://api-docs.deepseek.com/news/news260424 |
| DSpark meaning | DSpark variants are not new base models; the Hugging Face card says they are the same checkpoint with an additional speculative decoding module attached. | https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash-DSpark |
| Open weights | `deepseek-ai/DeepSeek-V4-Flash-DSpark` is MIT licensed on Hugging Face and references DeepSpec for inference details. | https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash-DSpark |
| Research claim | The DSpark paper describes confidence-scheduled speculative decoding and reports 60-85 percent per-user generation speedups over the MTP-1 baseline in DeepSeek-V4 serving. | https://arxiv.org/abs/2607.05147 |

## Raven Adoption Stance

Use DeepSeek V4 Flash + DSpark as Raven's cheap-first remote reasoning lane after privacy and policy checks pass. Use DeepSeek V4 Pro + DSpark as an escalation lane for harder architecture, code, long-document synthesis, and agent planning tasks.

Do not route raw PHI, private patient data, credentials, unpublished lab records, or user-private documents to DeepSeek by default. Those tasks should stay local-first through Hermes Edge, Ollama, LM Studio, or an institution-approved deployment boundary.

## Runtime Contract

The dependency-free provider profile lives in `runtime/provider_profiles.py`.

```python
from runtime.provider_profiles import ProviderRouteRequest, select_provider

decision = select_provider(
    ProviderRouteRequest(
        task="public literature synthesis",
        context_tokens=250_000,
        reasoning="medium",
        budget="lowest",
        requires_json=True,
    )
)

assert decision.profile.id == "deepseek-v4-flash-dspark"
```

The profile module does not make network calls. It only decides which model lane is appropriate and returns provider provenance tags that can be attached to Raven Evidence Graph traces.

## Ecosystem Fit

| App | DeepSeek DSpark role |
|---|---|
| Raven AI | Owns the central provider profile, routing policy, and Evidence Graph provenance tags. |
| OpenClinical AI | May use DeepSeek only for de-identified, policy-approved clinical admin/research workflows; raw PHI remains local or institution-approved. |
| Home for AI | Can expose DeepSeek Flash as a cheap-first cloud lane for user-approved long-context tasks while keeping private connector payloads local. |
| Hermes Edge | Remains the local/edge fallback and benchmark surface; DSpark is remote acceleration unless a self-hosted DeepSpec path is explicitly deployed. |

## Suggested Routing Policy

1. If the task is `private`, `phi`, or explicitly offline, choose `local-first-fallback`.
2. If context exceeds the configured DeepSeek window, segment or summarize locally before remote routing.
3. If the task is public/internal, latency-sensitive, budget-sensitive, JSON-oriented, or tool-oriented, choose `deepseek-v4-flash-dspark`.
4. If the task is public/internal, high-reasoning, premium budget, and not latency-sensitive, choose `deepseek-v4-pro-dspark`.
5. Always attach provider tags to evidence traces: `provider:deepseek`, `model:<model-id>`, and `profile:<profile-id>`.

## Implementation Notes

- Keep `DEEPSEEK_API_KEY` out of source control.
- Treat published prices and rate limits as volatile; verify the official pricing page before cost-sensitive production use.
- Use Evidence Graph to record which provider profile produced or transformed an answer.
- Use local redaction and source-ID references before sending large biomedical or clinical material to a remote model.
- Benchmark Raven workflows before claiming DSpark speedups, because DSpark is an inference acceleration method and application latency still depends on routing, retrieval, network, output length, and evidence extraction.

# Local NIM Sovereign Agent Lane

Updated: 2026-07-08
Status: reference adapter

## Purpose

Raven now has a local NVIDIA NIM sovereign-agent lane for teams that want on-prem or institution-controlled inference while preserving Raven's Evidence Graph, Token Economy, and Scientific Gates contracts.

This lane promotes the idea from the `simpliibarrii-crypto/langchain-nvidia` fork branch `feat/local-nim-sovereign-agent-example` into Raven's own runtime contracts.

## Files

- `runtime/local_nim_sovereign.py` — dependency-light Raven adapter for OpenAI-compatible NIM endpoints.
- `examples/local_nim_sovereign_agent.py` — runnable synthetic demo.
- `tests/test_local_nim_sovereign.py` — unit tests with a fake NIM client.

## Correct lane model

| Device or deployment | Recommended lane |
|---|---|
| NVIDIA workstation, private cloud, institution server | Local NIM sovereign lane |
| iPhone / mobile edge | Hermes Edge, LiteRT, Core ML, or other phone-native runtime |
| Small CPU/GPU mini-PC | Ollama, llama.cpp, vLLM, or lightweight local lane |
| Public demo web app | Replit for prototype, Vercel for polished deployment |

NIM should be presented as a premium sovereign/on-prem lane, not as the default iPhone-local path.

## Run the demo

Start a local NIM-compatible chat endpoint, then run:

```bash
python examples/local_nim_sovereign_agent.py \
  --base-url http://localhost:8000/v1 \
  --model meta/llama-3.1-70b-instruct
```

The demo writes a JSON artifact to:

```text
artifacts/local_nim_sovereign_agent.json
```

## What the adapter emits

`run_local_nim_sovereign_agent(...)` returns a `SovereignAgentResult` containing:

- `run_id`
- `answer`
- `evidence_graph` with schema `raven.evidence_graph.v1`
- compact `evidence_trace`
- Token Economy metadata
- Scientific Gate report

## Public-claim safety

The adapter is designed to make local inference reviewable. It does not claim clinical validation, benchmark leadership, or autonomous discovery.

A run should not be published if:

- the Gate report has `can_publish = false`,
- the run contains PHI,
- the evidence sources are synthetic but marketed as real validation,
- model speed/cost claims lack benchmark receipts,
- clinical language outruns human review.

## Integration path

1. Keep `runtime/local_nim_sovereign.py` as the Raven source-of-truth adapter.
2. Use the existing LangChain fork example as upstream/reference material.
3. Add a Hermes Edge note that NIM is the on-prem GPU lane while Hermes remains the mobile/edge lane.
4. Add a Home for AI UI panel that displays the JSON result: answer, claims, sources, confidence, risk, and gate status.
5. Add a Replit synthetic demo for fast public explanation.
6. Add a Vercel polished explainer once the adapter and docs are stable.
7. Only post public claims with the gate report and artifact path attached.

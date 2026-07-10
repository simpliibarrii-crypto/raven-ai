# Local NIM Sovereign Agent Integration

Updated: 2026-07-08
Status: reference integration plan
Source signal: `simpliibarrii-crypto/langchain-nvidia`, branch `feat/local-nim-sovereign-agent-example`

## What already exists

The forked `langchain-nvidia` repository contains a proof-of-concept file:

```text
cookbook/local_nim_sovereign_agent.py
```

That example shows the core idea:

- use `ChatNVIDIA(base_url="http://localhost:8000/v1")` against a self-hosted NIM-compatible endpoint,
- wrap the call in a LangGraph workflow,
- attach a minimal evidence trace,
- frame the pattern as a Raven-style sovereign/local agent.

Raven now carries a more Raven-native reference version at:

```text
examples/local_nim_sovereign_agent.py
```

## Why it matters

This is a strong fit for the Raven ecosystem because Raven already treats trustworthy scientific agents as a stack:

1. local or institution-approved inference where privacy matters,
2. Evidence Graph tracing for sources, claims, confidence, risk, and provenance,
3. Token Economy routing for cheap draft, selective verification, and escalation control,
4. Scientific Gates for publishability, reproducibility, metrics, replay commands, and restrained public claims.

## Correct architecture

NIM should be a premium sovereign inference lane, not the only local lane.

| Device or environment | Preferred lane |
|---|---|
| iPhone / mobile | Hermes Edge, Core ML, LiteRT-LM, llama.cpp-style mobile runtimes |
| Mini PC without NVIDIA GPU | Ollama, llama.cpp, CPU/Apple/AMD-friendly local runtimes |
| NVIDIA workstation/server | local NIM, NVIDIA Dynamo, TensorRT-LLM, Triton/NIM stack |
| Institution/private cloud | NIM or vLLM behind approved boundary |
| Public demo | Replit or Vercel surface backed by synthetic data only |

## Run the reference example

The example requires a local NIM-compatible endpoint.

```bash
python examples/local_nim_sovereign_agent.py \
  --base-url http://localhost:8000/v1 \
  --model meta/llama-3.1-70b-instruct \
  --question "Summarize this synthetic handoff note safely." \
  --source-text "Synthetic note: resident reports poor sleep and mild cough. No PHI."
```

Optional dependencies:

```bash
pip install langchain-nvidia-ai-endpoints langchain-core
```

Expected output artifact:

```text
artifacts/local_nim_sovereign_agent.json
```

The artifact includes:

- answer,
- NIM route metadata,
- Token Economy plan,
- `raven.evidence_graph.v1` packet,
- Scientific Gate report,
- limitations.

## Production rules

Do not claim:

- clinical validation,
- autonomous discovery,
- state-of-the-art performance,
- iPhone NIM support,
- benchmark improvement,
- medical-device readiness.

Do claim only:

- Raven can emit a source-linked Evidence Graph packet,
- Raven can attach Token Economy metadata to local/sovereign inference,
- Raven can run Scientific Gates before public claims,
- NIM is one possible sovereign lane when NVIDIA infrastructure exists.

## Next steps

1. Add a unit test using a fake NIM client so CI does not require NVIDIA hardware.
2. Add a provider profile named `local_nim` in Raven provider profiles.
3. Add a release receipt showing synthetic input, evidence packet, token plan, and gate report.
4. Link the example from README after the test exists.
5. Create a Replit visual prototype using synthetic data only.
6. Create a Vercel public page only after the release receipt is complete.

## Suggested public wording

> Raven AI is adding a sovereign local-inference lane for scientific agents: local NIM where NVIDIA infrastructure exists, lightweight local runtimes for edge devices, and Evidence Graph tracing across both. The point is not louder AI. The point is reviewable AI.

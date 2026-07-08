# Raven AI

![Raven AI](assets/raven-ai-banner.svg)

[![License](https://img.shields.io/github/license/simpliibarrii-crypto/raven-ai?style=for-the-badge)](LICENSE)
[![Live Demo](https://img.shields.io/badge/%F0%9F%A4%97-Live%20Demo-FFD21E?style=for-the-badge)](https://huggingface.co/spaces/bclermo/raven-ai)

## ⚡ Quick Start

```bash
pip install raven-ai
raven serve --port 8000
```

Or try the **[Live Demo on Hugging Face Spaces](https://huggingface.co/spaces/bclermo/raven-ai)** — no installation required.
[![CI](https://img.shields.io/github/actions/workflow/status/simpliibarrii-crypto/raven-ai/ci-python.yml?branch=main&style=for-the-badge&label=CI)](https://github.com/simpliibarrii-crypto/raven-ai/actions)
[![Flagship](https://img.shields.io/badge/flagship-Raven_AI-C8102E?style=for-the-badge&labelColor=05060A)](https://github.com/simpliibarrii-crypto/raven-ai)

**Raven AI is an open-source biology and healthcare agent platform for labs, researchers, classrooms, startups, and clinical teams.**

Raven is the flagship product in the ecosystem: a local-first, cloud-optional platform for agentic AI, computational biology, clinical evidence workflows, and reproducible scientific automation.

## Ecosystem surfaces

| Surface | Purpose |
|---|---|
| Raven Bio | Genomics, transcriptomics, proteomics, structural biology, wet-lab planning |
| Raven Clinical | Healthcare evidence, calculators, terminology, PHI-aware workflows |
| Raven LabOps | Protocol execution, sample tracking, instrument coordination, audit logs |
| Raven Research | Literature review, citation verification, hypotheses, reproducible reports |

## Raven Evidence Graph

Raven Evidence Graph is the dependency-free provenance layer for claims, sources, confidence, risk, and answer traces. It gives Raven agents a compact JSON contract that can travel cleanly across OpenClinical AI, Home for AI, Hermes Edge, notebooks, demos, and audit logs.

```python
from runtime.evidence_graph import EvidenceGraph

graph = EvidenceGraph()
source = graph.add_source(title="Protocol v1", kind="protocol")
claim = graph.add_claim("Audit logs should preserve signed consent context.", [source.id])
trace = graph.trace_answer("What should this workflow preserve?", [claim.id])
```

See [docs/EVIDENCE_GRAPH.md](docs/EVIDENCE_GRAPH.md) for the data model, scoring contract, and integration notes.

## Raven Token Economy

Raven studies DSpark's useful token-saving principle without depending on DeepSeek directly: draft cheaply, verify by confidence/risk/evidence, reuse cache, retrieve narrow slices, and escalate only when the cheap draft fails.

```python
from runtime.token_economy import TokenEconomyRequest, plan_token_economy

plan = plan_token_economy(TokenEconomyRequest(task="public literature synthesis", cache_hit_ratio=0.4))
print(plan.actions)
```

See [docs/TOKEN_ECONOMY.md](docs/TOKEN_ECONOMY.md) for the product policy and [docs/DEEPSEEK_DSPARK.md](docs/DEEPSEEK_DSPARK.md) for the research note.

## Scientific Agent Gates

Raven now includes dependency-free scientific run gates that check claim-level evidence labels, reproducibility artifacts, metrics, Token Economy metadata, PHI routing, and public-claim safety before a scientific-agent output is treated as publishable.

```python
from runtime.scientific_agent_gates import ScientificRunManifest, evaluate_scientific_run

report = evaluate_scientific_run(ScientificRunManifest(
    run_id="run-001",
    task_id="bio-task-001",
    question="What does this run test?",
    hypothesis="Evidence-linked runs are easier to audit.",
    workflow_stage="literature_review",
))
print(report.status)
```

See [docs/SCIENTIFIC_AGENT_GATES.md](docs/SCIENTIFIC_AGENT_GATES.md) for the research mapping and gate contract.

## Ecosystem operations

See [docs/ECOSYSTEM_OPERATIONS.md](docs/ECOSYSTEM_OPERATIONS.md) for the unified roadmap, repo roles, demo rules, and immediate backlog.

## Demo video

Watch the clean Raven Evidence Graph demo on X: https://x.com/i/web/status/2074684335639187945

The video is generated from pure code with no Replit, HeyGen, React Flow, stock, or generator watermark. See [docs/CLEAN_DEMO_VIDEO.md](docs/CLEAN_DEMO_VIDEO.md) and [scripts/render_clean_demo_video.py](scripts/render_clean_demo_video.py).

## Repository status

This repository contains the active Raven platform work plus architecture previews. The Python runtime and clinical/home-care substrate are the current working foundation. Rust, Flutter, and mobile modules are being hardened behind CI before being promoted as stable.

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e . pytest pynacl
pytest -q
```

## Architecture

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Roadmap

See [ROADMAP.md](ROADMAP.md).

## Security

Report security issues privately. See [SECURITY.md](SECURITY.md).

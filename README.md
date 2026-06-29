# Raven AI

![Raven AI](assets/raven-ai-banner.svg)

[![License](https://img.shields.io/github/license/simpliibarrii-crypto/raven-ai?style=for-the-badge)](LICENSE)
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

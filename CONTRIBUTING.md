# Contributing to openclinical-ai

Thanks for your interest in contributing. This project is built by frontline Canadian healthcare workers + AI engineers + sovereign-infrastructure advocates.

## How to contribute

1. **Issues** — file a GitHub issue for bugs, missing features, or research questions.
2. **Pull requests** — fork the repo, make focused changes, submit a PR.
3. **CLA** — all contributions require a Contributor License Agreement. This protects both contributors and the open-source license. Email `bclerjuste@gmail.com` to get the CLA.
4. **Code review** — all PRs require review from a maintainer.

## Areas where contributions are especially welcome

- **Biology AI adapters** — protein folding, variant effect prediction, RNA structure, drug-target interaction
- **Clinical NLP adapters** — PSW note structuring, clinical documentation, multilingual support (FR/EN priority)
- **FHIR integration** — Consent resource, AuditEvent, Patient, Observation
- **Adversarial-robustness CI** — red-teaming pipelines, prompt-injection detection, input sanitization
- **Edge deployment** — Jetson Orin, Coral, Hailo, Raspberry Pi inference
- **Compliance** — PHIPA, PIPEDA, EU AI Act, FDA PCCP mapping
- **Documentation** — translations (especially French Canadian), tutorials, case studies

## Coding standards

- Python 3.10+ with type hints
- `ruff` for linting, `black` for formatting (config to come)
- `pytest` for tests — PRs without tests will be reviewed but may be held
- Apache 2.0 license headers on all new files

## Commit message format

```
<scope>: <short description>

<longer description>

Refs: <issue or research doc>
```

Examples:
- `runtime: add consent revocation endpoint`
- `psw-ui: support French Canadian voice input`
- `biology-ai: scaffold protein-fold adapter`
- `docs: update THREAT-MODEL.md with prompt-injection analysis`

## Code of conduct

This is a healthcare project. Be respectful, professional, and patient-first. We are building infrastructure that affects real people's lives.

---

Questions? Email `bclerjuste@gmail.com` or open a GitHub discussion.
# Raven BioComputer incubator

This directory seeds **Raven BioComputer**, a planned standalone repository that gives biology agents a bounded, auditable workstation instead of unrestricted access to the host computer.

The MVP includes private run folders, deterministic DNA tools, JSpace policy gates, Raven Evidence Graph receipts, and bridge records for Home for AI, Hermes Edge, and OpenClinical AI. Sensitive clinical, wet-lab, genome-editing, pathogen, credential, shell, and exfiltration requests are blocked or routed to human review.

## Run

```bash
python -m pip install -e ".[dev]"
pytest
```

```python
from raven_biocomputer import BioComputer

receipt = BioComputer().execute(
    task="Inspect a demonstration sequence",
    tool="sequence_stats",
    payload={"sequence": "ACGTACGTNN"},
)
```

The full standalone repository package, including FastAPI, MCP, Docker, schemas, documentation, and Hugging Face Space metadata, is generated separately for migration to `simpliibarrii-crypto/raven-biocomputer` and `bclermo/raven-biocomputer`.

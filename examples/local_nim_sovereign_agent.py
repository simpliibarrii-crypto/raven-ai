"""Run Raven through a local NVIDIA NIM sovereign-agent lane.

Prerequisite: a local or institution-hosted OpenAI-compatible NIM endpoint,
for example `http://localhost:8000/v1`.

This example uses synthetic source text. Do not paste PHI into public demos.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime.local_nim_sovereign import LocalNIMConfig, NIMSource, run_local_nim_sovereign_agent


def main() -> None:
    parser = argparse.ArgumentParser(description="Raven local NIM sovereign-agent demo")
    parser.add_argument("--base-url", default="http://localhost:8000/v1")
    parser.add_argument("--model", default="meta/llama-3.1-70b-instruct")
    parser.add_argument("--question", default="What does the synthetic handoff note say changed during the shift?")
    parser.add_argument("--contains-phi", action="store_true", help="Mark the run private/non-publishable for PHI-bearing workflows.")
    parser.add_argument("--output", default="artifacts/local_nim_sovereign_agent.json")
    args = parser.parse_args()

    synthetic_sources = [
        NIMSource(
            title="Synthetic PSW handoff note",
            text=(
                "Synthetic resident was calm during the evening observation. "
                "No fall was observed in this synthetic scenario. "
                "Hydration reminders were provided twice. "
                "The note is not real patient data and is for Raven testing only."
            ),
            kind="synthetic-note",
            quality=0.82,
        ),
        NIMSource(
            title="Raven local-demo policy",
            text=(
                "Raven demo outputs should remain source-linked, uncertainty-aware, "
                "and reviewed before any clinical or public claim. "
                "Synthetic examples must not be presented as real clinical validation."
            ),
            kind="policy",
            quality=0.88,
        ),
    ]

    result = run_local_nim_sovereign_agent(
        question=args.question,
        sources=synthetic_sources,
        config=LocalNIMConfig(base_url=args.base_url, model=args.model),
        contains_phi=args.contains_phi,
    )

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(result.to_json(), encoding="utf-8")

    print(json.dumps({
        "run_id": result.run_id,
        "output": str(output),
        "gate_status": result.gate_report.status,
        "can_publish": result.gate_report.can_publish,
    }, indent=2))
    if not result.gate_report.can_publish:
        print("\nGate note: this run is not publishable without resolving required actions.")


if __name__ == "__main__":
    main()

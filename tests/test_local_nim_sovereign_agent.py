from __future__ import annotations

import argparse
import json

from examples.local_nim_sovereign_agent import build_token_plan, run_demo


def test_local_nim_demo_can_run_with_mock_answer(tmp_path):
    output = tmp_path / "local_nim_artifact.json"
    args = argparse.Namespace(
        base_url="http://localhost:8000/v1",
        model="meta/llama-3.1-70b-instruct",
        question="Summarize this synthetic note safely.",
        source_text="Synthetic note: resident reports poor sleep. No PHI is included.",
        output=str(output),
        mock_answer="The synthetic note reports poor sleep. This is not clinical advice.",
    )

    artifact = run_demo(args)
    saved = json.loads(output.read_text())

    assert artifact["schema"] == "raven.local_nim_sovereign_agent.demo.v1"
    assert saved["evidence_trace"]["schema"] == "raven.evidence_graph.v1"
    assert saved["token_economy"]["provider_lane"] == "local_nim"
    assert saved["token_economy"]["sovereign_mode"] is True
    assert saved["gate_report"]["status"] in {"pass", "warn"}


def test_local_nim_token_plan_uses_local_private_lane():
    plan = build_token_plan("Summarize synthetic note safely.")

    assert plan["draft_lane"] in {"local-small", "local-large"}
    assert plan["provider_lane"] == "local_nim"
    assert plan["sovereign_mode"] is True
    assert "verification_spans" in plan

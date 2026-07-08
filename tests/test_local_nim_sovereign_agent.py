from __future__ import annotations

import importlib.util
from pathlib import Path


def load_example_module():
    path = Path(__file__).resolve().parents[1] / "examples" / "local_nim_sovereign_agent.py"
    spec = importlib.util.spec_from_file_location("local_nim_sovereign_agent", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_reference_example_builds_evidence_packet_without_nim_dependencies(tmp_path):
    module = load_example_module()

    question = "Summarize this synthetic note safely."
    answer = "The synthetic note reports poor sleep and mild cough; no clinical recommendation is made."
    source_text = "Synthetic note: resident reports poor sleep and mild cough. No PHI is included."

    graph = module.build_evidence_graph(question=question, answer=answer, source_text=source_text)
    packet = graph.to_dict()

    assert packet["schema"] == "raven.evidence_graph.v1"
    assert packet["sources"]
    assert packet["claims"]
    assert any("agent-output" in claim.get("labels", []) for claim in packet["claims"])

    token_plan = module.build_token_plan(question)
    assert token_plan["draft_lane"] in {"local-small", "local-large"}
    assert token_plan["provider_lane"] == "local_nim"
    assert token_plan["sovereign_mode"] is True
    assert token_plan["verification_spans"]

    output_path = tmp_path / "local_nim_sovereign_agent.json"
    gate_report = module.build_gate_report(
        question=question,
        evidence_packet=packet,
        token_plan=token_plan,
        output_path=output_path,
    )

    assert gate_report["run_id"] == "local-nim-sovereign-demo"
    assert gate_report["status"] in {"pass", "warn"}
    assert gate_report["can_publish"] in {True, False}
    assert not gate_report["required_actions"]


def test_call_local_nim_has_clear_optional_dependency_error(monkeypatch):
    module = load_example_module()

    real_import = __import__

    def fake_import(name, *args, **kwargs):
        if name == "langchain_nvidia_ai_endpoints":
            raise ImportError("missing test dependency")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr("builtins.__import__", fake_import)

    try:
        module.call_local_nim(
            base_url="http://localhost:8000/v1",
            model="meta/llama-3.1-70b-instruct",
            question="test",
            source_text="synthetic",
        )
    except RuntimeError as exc:
        assert "Install optional NIM demo dependencies" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("expected missing optional dependency error")

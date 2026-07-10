from __future__ import annotations

import json

from runtime.local_nim_sovereign import (
    LocalNIMConfig,
    NIMSource,
    run_local_nim_sovereign_agent,
)


class FakeNIMClient:
    def __init__(self) -> None:
        self.messages: list[dict[str, str]] | None = None
        self.max_tokens: int | None = None
        self.temperature: float | None = None

    def complete(self, messages: list[dict[str, str]], *, max_tokens: int, temperature: float) -> str:
        self.messages = messages
        self.max_tokens = max_tokens
        self.temperature = temperature
        return "The synthetic note reports a stable observation and hydration reminders. This is not clinical validation."


def test_local_nim_sovereign_agent_emits_raven_packets() -> None:
    client = FakeNIMClient()
    result = run_local_nim_sovereign_agent(
        question="What changed during the synthetic shift?",
        sources=[
            NIMSource(
                title="Synthetic handoff note",
                text="Synthetic resident remained stable. Hydration reminders were provided twice. No real patient data is included.",
                kind="synthetic-note",
                quality=0.84,
            )
        ],
        client=client,
        config=LocalNIMConfig(model="test-local-nim", max_tokens=512),
    )

    assert result.run_id.startswith("local-nim:")
    assert result.evidence_graph["schema"] == "raven.evidence_graph.v1"
    assert result.evidence_trace["schema"] == "raven.evidence_graph.v1"
    assert result.token_economy["draft_lane"] in {"local-small", "local-large"}
    assert result.gate_report.status in {"pass", "warn"}
    assert client.messages is not None
    assert "Synthetic handoff note" in client.messages[-1]["content"]
    assert client.max_tokens == result.token_economy["max_output_tokens"]
    assert json.loads(result.to_json())["run_id"] == result.run_id


def test_phi_run_is_not_publishable() -> None:
    result = run_local_nim_sovereign_agent(
        question="Summarize private synthetic note.",
        sources=[
            NIMSource(
                title="Private synthetic note",
                text="Synthetic private context for testing only. No real PHI is included in this unit test.",
            )
        ],
        client=FakeNIMClient(),
        contains_phi=True,
    )

    assert result.token_economy["draft_lane"] == "local-large"
    assert result.gate_report.can_publish is False
    assert any(finding.code == "phi-private-output" for finding in result.gate_report.findings)


def test_requires_question_and_sources() -> None:
    try:
        run_local_nim_sovereign_agent(question="", sources=[NIMSource(title="x", text="source text")], client=FakeNIMClient())
    except ValueError as exc:
        assert "question" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("empty question should fail")

    try:
        run_local_nim_sovereign_agent(question="Valid?", sources=[], client=FakeNIMClient())
    except ValueError as exc:
        assert "source" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("missing sources should fail")

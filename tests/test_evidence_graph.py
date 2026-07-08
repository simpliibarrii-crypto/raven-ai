from __future__ import annotations

import json

from runtime.evidence_graph import EvidenceGraph, extract_entities, highest_risk, split_claims


def test_ingest_document_creates_source_claims_and_edges():
    graph = EvidenceGraph()
    claims = graph.ingest_document(
        title="OpenClinical shift handoff note",
        kind="clinical-note",
        uri="local://handoff/demo",
        quality=0.8,
        labels=["handoff", "clinical"],
        text=(
            "Patient consent was granted for PSW shift handoff summarization. "
            "The clinical workflow records audit events for every inference. "
            "Raven AI keeps evidence linked to sources for review."
        ),
    )

    assert len(graph.sources) == 1
    assert len(claims) == 3
    assert all(claim.source_ids for claim in claims)
    assert any(edge.relation == "supports" for edge in graph.edges)
    assert claims[0].risk == "high"


def test_explain_claim_scores_from_confidence_quality_and_risk():
    graph = EvidenceGraph()
    source = graph.add_source("Benchmark contract", "doc", quality=0.9)
    claim = graph.add_claim(
        "Benchmark claims require device, backend, memory, and token throughput evidence.",
        source_ids=[source.id],
        confidence=0.85,
        risk="medium",
    )

    explanation = graph.explain_claim(claim.id)

    assert explanation["score"] > 0.6
    assert explanation["risk"] == "medium"
    assert explanation["sources"][0]["title"] == "Benchmark contract"
    assert "Benchmark contract" in explanation["explanation"]


def test_trace_answer_aggregates_claims_and_sources():
    graph = EvidenceGraph()
    source = graph.add_source("Raven README", "readme", quality=0.75)
    c1 = graph.add_claim("Raven AI is a local-first scientific AI platform.", [source.id], confidence=0.8, risk="low")
    c2 = graph.add_claim("Clinical workflows need consent and audit boundaries.", [source.id], confidence=0.7, risk="high")

    trace = graph.trace_answer("Raven should explain why each answer is supported.", [c1.id, c2.id])

    assert trace.confidence > 0
    assert trace.risk == "high"
    assert trace.source_ids == (source.id,)
    assert trace.claim_ids == (c1.id, c2.id)


def test_json_round_trip_preserves_graph_contents():
    graph = EvidenceGraph()
    graph.ingest_document(
        title="Hermes Edge policy",
        kind="readme",
        quality=0.7,
        text="Hermes Edge routes deterministic tools before model calls. Local-first routing reduces avoidable cloud use.",
    )

    payload = graph.to_json()
    loaded = EvidenceGraph.from_json(payload)

    assert json.loads(payload)["schema"] == "raven.evidence_graph.v1"
    assert loaded.to_dict()["sources"] == graph.to_dict()["sources"]
    assert loaded.to_dict()["claims"] == graph.to_dict()["claims"]
    assert loaded.to_dict()["edges"] == graph.to_dict()["edges"]


def test_text_helpers_are_deterministic():
    claims = split_claims("Short. Raven Clinical links consent to audit logs. Evidence Graph tracks provenance.")
    entities = extract_entities("Raven Clinical Evidence Graph supports consent audit workflows.")

    assert claims == ["Raven Clinical links consent to audit logs.", "Evidence Graph tracks provenance."]
    assert "Raven" in entities
    assert "Clinical" in entities
    assert highest_risk(["low", "critical", "medium"]) == "critical"

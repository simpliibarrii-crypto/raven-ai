from __future__ import annotations

from fastapi.testclient import TestClient

from runtime.server import create_app


def test_health_capabilities_and_readiness(tmp_path):
    with TestClient(create_app(tmp_path)) as client:
        health = client.get("/health")
        assert health.status_code == 200
        assert health.json()["service"] == "raven-ai"

        ready = client.get("/ready")
        assert ready.status_code == 200
        assert "raven.evidence_graph.v1" in ready.json()["contracts"]

        capabilities = client.get("/v1/capabilities")
        assert capabilities.status_code == 200
        features = capabilities.json()["features"]
        assert features["evidence_graph"] is True
        assert features["clinical_tenancy"] is False


def test_evidence_ingest_and_trace(tmp_path):
    with TestClient(create_app(tmp_path)) as client:
        response = client.post(
            "/v1/evidence/ingest",
            json={
                "documents": [
                    {
                        "title": "Protocol",
                        "text": (
                            "The protocol records a stable environment fingerprint. "
                            "Every published claim links to a source record."
                        ),
                        "kind": "protocol",
                        "quality": 0.9,
                    }
                ]
            },
        )
        assert response.status_code == 200
        graph = response.json()
        assert graph["schema"] == "raven.evidence_graph.v1"
        assert len(graph["claims"]) == 2

        claim_ids = [claim["id"] for claim in graph["claims"]]
        trace = client.post(
            "/v1/evidence/trace",
            json={
                "graph": graph,
                "answer": "The run is designed for reproducibility and provenance.",
                "claim_ids": claim_ids,
            },
        )
        assert trace.status_code == 200
        assert trace.json()["claim_ids"] == claim_ids
        assert trace.json()["confidence"] > 0


def test_token_plan_and_verification_schedule(tmp_path):
    with TestClient(create_app(tmp_path)) as client:
        plan = client.post(
            "/v1/token-economy/plan",
            json={
                "task": "Verify a public literature synthesis",
                "complexity": "research",
                "risk": "high",
                "estimated_context_tokens": 50_000,
                "estimated_output_tokens": 1_000,
                "requires_exact_citations": True,
                "evidence_coverage": 0.8,
            },
        )
        assert plan.status_code == 200
        payload = plan.json()
        assert payload["schema"] == "raven.token_economy.v1"
        assert payload["verification_token_budget"] > 0

        schedule = client.post(
            "/v1/token-economy/verification",
            json={
                "spans": [
                    {
                        "label": "well-supported",
                        "confidence": 0.95,
                        "risk": "low",
                        "evidence_coverage": 0.9,
                    },
                    {
                        "label": "critical-uncertain",
                        "confidence": 0.2,
                        "risk": "critical",
                        "evidence_coverage": 0.1,
                    },
                ]
            },
        )
        assert schedule.status_code == 200
        selected = schedule.json()["spans_to_verify"]
        assert any(span["label"] == "critical-uncertain" for span in selected)


def test_scientific_run_persistence_and_human_approval(tmp_path):
    manifest = {
        "run_id": "run-001",
        "task_id": "task-001",
        "question": "Does the workflow preserve provenance?",
        "hypothesis": "Evidence-linked runs are easier to audit.",
        "workflow_stage": "literature_review",
        "risk": "medium",
        "sources": [
            {
                "id": "src-001",
                "title": "Protocol",
                "kind": "protocol",
            }
        ],
        "claim_checks": [
            {
                "claim_id": "claim-001",
                "claim": "The run records source provenance.",
                "evidence_label": "support",
                "source_ids": ["src-001"],
                "confidence": 0.9,
            }
        ],
        "evidence_trace": {
            "schema": "raven.evidence_graph.v1",
            "sources": [],
            "claims": [],
            "edges": [],
        },
        "token_economy": {
            "draft_lane": "local-small",
            "context_budget": 2_000,
            "estimated_saved_context_tokens": 500,
            "confidence_floor": 0.7,
            "verification_spans": [],
        },
    }

    with TestClient(create_app(tmp_path)) as client:
        evaluated = client.post(
            "/v1/scientific-runs/evaluate",
            json={"manifest": manifest, "persist": True},
        )
        assert evaluated.status_code == 200
        assert evaluated.json()["run_id"] == "run-001"

        stored = client.get("/v1/runs/run-001")
        assert stored.status_code == 200
        assert stored.json()["schema"] == "raven.scientific_run.v1"

        approved = client.post(
            "/v1/runs/run-001/approvals",
            json={
                "reviewer": "scientific-reviewer",
                "decision": "approved",
                "note": "Evidence links reviewed.",
            },
        )
        assert approved.status_code == 200
        assert approved.json()["human_decision"] == "approved"
        assert len(approved.json()["approvals"]) == 1


def test_run_id_rejects_unsafe_characters(tmp_path):
    with TestClient(create_app(tmp_path)) as client:
        response = client.get("/v1/runs/bad$id")
        assert response.status_code == 422

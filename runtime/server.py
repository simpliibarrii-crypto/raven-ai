"""Raven AI FastAPI runtime.

This module exposes Raven's native contracts:
- evidence ingestion and provenance traces
- token-economy planning and confidence-scheduled verification
- scientific-agent publication gates
- replayable run records with explicit human approvals

Clinical tenancy, consent, visits, and FHIR workflows belong in openclinical-ai.
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import time
from contextlib import asynccontextmanager
from dataclasses import asdict
from pathlib import Path
from typing import Any, AsyncIterator

from fastapi import FastAPI, HTTPException, Request, status
from pydantic import BaseModel, Field

from runtime import __version__
from runtime.evidence_graph import EvidenceGraph
from runtime.scientific_agent_gates import (
    ScientificClaimCheck,
    ScientificRunManifest,
    evaluate_scientific_run,
)
from runtime.token_economy import (
    TokenEconomyRequest,
    VerificationSpan,
    plan_token_economy,
    schedule_verification,
)

_RUN_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


class EvidenceDocument(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    text: str = Field(min_length=1, max_length=500_000)
    kind: str = Field(default="document", min_length=1, max_length=80)
    uri: str | None = Field(default=None, max_length=2_000)
    quality: float = Field(default=0.5, ge=0.0, le=1.0)
    labels: list[str] = Field(default_factory=list)
    max_claims: int = Field(default=12, ge=1, le=100)


class EvidenceIngestRequest(BaseModel):
    documents: list[EvidenceDocument] = Field(min_length=1, max_length=50)


class EvidenceTraceRequest(BaseModel):
    graph: dict[str, Any]
    answer: str = Field(min_length=1, max_length=100_000)
    claim_ids: list[str] = Field(default_factory=list, max_length=500)


class TokenPlanRequest(BaseModel):
    task: str = Field(min_length=1, max_length=20_000)
    complexity: str = "standard"
    risk: str = "medium"
    privacy: str = "public"
    estimated_context_tokens: int = Field(default=0, ge=0)
    estimated_output_tokens: int = Field(default=512, ge=1, le=65_536)
    cache_hit_ratio: float = Field(default=0.0, ge=0.0, le=1.0)
    draft_confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    evidence_coverage: float = Field(default=0.0, ge=0.0, le=1.0)
    system_load: float = Field(default=0.0, ge=0.0, le=1.0)
    latency_sensitive: bool = False
    requires_exact_citations: bool = False
    tool_available: bool = False
    local_model_available: bool = True


class VerificationSpanRequest(BaseModel):
    label: str = Field(min_length=1, max_length=500)
    confidence: float = Field(ge=0.0, le=1.0)
    risk: str = "medium"
    evidence_coverage: float = Field(default=0.0, ge=0.0, le=1.0)


class VerificationRequest(BaseModel):
    spans: list[VerificationSpanRequest] = Field(default_factory=list, max_length=1_000)
    base_tokens_per_span: int = Field(default=96, ge=1, le=8_192)
    system_load: float = Field(default=0.0, ge=0.0, le=1.0)


class ScientificRunRequest(BaseModel):
    manifest: dict[str, Any]
    persist: bool = True


class ApprovalRequest(BaseModel):
    reviewer: str = Field(min_length=1, max_length=200)
    decision: str = Field(pattern=r"^(approved|rejected|needs_changes)$")
    note: str = Field(default="", max_length=10_000)


class RunStore:
    """Small local-first JSON run store with atomic writes."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self._lock = asyncio.Lock()

    @staticmethod
    def validate_run_id(run_id: str) -> str:
        if not _RUN_ID_RE.fullmatch(run_id):
            raise ValueError("run_id must contain only letters, numbers, dots, dashes, or underscores")
        return run_id

    def _path(self, run_id: str) -> Path:
        return self.root / f"{self.validate_run_id(run_id)}.json"

    async def save(self, record: dict[str, Any]) -> None:
        run_id = str(record.get("run_id", ""))
        path = self._path(run_id)
        tmp_path = path.with_suffix(".json.tmp")
        encoded = json.dumps(record, indent=2, sort_keys=True)
        async with self._lock:
            tmp_path.write_text(encoded, encoding="utf-8")
            tmp_path.replace(path)

    async def get(self, run_id: str) -> dict[str, Any] | None:
        path = self._path(run_id)
        if not path.exists():
            return None
        async with self._lock:
            return json.loads(path.read_text(encoding="utf-8"))

    async def list(self, limit: int = 100) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        async with self._lock:
            paths = sorted(
                self.root.glob("*.json"),
                key=lambda path: path.stat().st_mtime,
                reverse=True,
            )[:limit]
            for path in paths:
                try:
                    records.append(json.loads(path.read_text(encoding="utf-8")))
                except (OSError, json.JSONDecodeError):
                    continue
        return records


def _utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _build_manifest(payload: dict[str, Any]) -> ScientificRunManifest:
    data = dict(payload)
    claim_checks = []
    for raw in data.pop("claim_checks", ()) or ():
        item = dict(raw)
        item["source_ids"] = tuple(item.get("source_ids", ()) or ())
        claim_checks.append(ScientificClaimCheck(**item))

    for tuple_field in ("sources", "code_artifacts", "output_artifacts"):
        data[tuple_field] = tuple(data.get(tuple_field, ()) or ())
    data["claim_checks"] = tuple(claim_checks)
    return ScientificRunManifest(**data)


def _store_from_request(request: Request) -> RunStore:
    store = getattr(request.app.state, "run_store", None)
    if store is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "run store is not ready")
    return store


def create_app(runtime_root: Path | None = None) -> FastAPI:
    root = runtime_root or Path(
        os.getenv("RAVEN_RUNTIME_ROOT", str(Path.cwd() / ".runtime" / "raven"))
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.started_at = time.time()
        app.state.run_store = RunStore(root / "runs")
        yield

    app = FastAPI(
        title="Raven AI",
        version=__version__,
        description="Local-first scientific agent runtime with evidence and replay gates.",
        lifespan=lifespan,
    )

    @app.get("/health", tags=["system"])
    async def health(request: Request) -> dict[str, Any]:
        return {
            "status": "ok",
            "service": "raven-ai",
            "version": __version__,
            "uptime_seconds": round(time.time() - request.app.state.started_at, 3),
        }

    @app.get("/ready", tags=["system"])
    async def ready(request: Request) -> dict[str, Any]:
        store = _store_from_request(request)
        return {
            "status": "ready",
            "run_store": str(store.root),
            "contracts": [
                "raven.evidence_graph.v1",
                "raven.token_economy.v1",
                "raven.scientific_run.v1",
            ],
        }

    @app.get("/v1/capabilities", tags=["system"])
    async def capabilities() -> dict[str, Any]:
        return {
            "service": "raven-ai",
            "version": __version__,
            "features": {
                "evidence_graph": True,
                "token_economy": True,
                "scientific_gates": True,
                "run_persistence": True,
                "human_approval": True,
                "clinical_tenancy": False,
            },
            "clinical_runtime": "openclinical-ai",
        }

    @app.post("/v1/evidence/ingest", tags=["evidence"])
    async def ingest_evidence(body: EvidenceIngestRequest) -> dict[str, Any]:
        graph = EvidenceGraph()
        for document in body.documents:
            graph.ingest_document(
                title=document.title,
                text=document.text,
                kind=document.kind,
                uri=document.uri,
                quality=document.quality,
                labels=document.labels,
                max_claims=document.max_claims,
            )
        return graph.to_dict()

    @app.post("/v1/evidence/trace", tags=["evidence"])
    async def trace_evidence(body: EvidenceTraceRequest) -> dict[str, Any]:
        try:
            graph = EvidenceGraph.from_dict(body.graph)
            return asdict(graph.trace_answer(body.answer, body.claim_ids))
        except (KeyError, TypeError, ValueError) as exc:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc

    @app.post("/v1/token-economy/plan", tags=["routing"])
    async def token_plan(body: TokenPlanRequest) -> dict[str, Any]:
        try:
            request_data = body.model_dump()
            plan = plan_token_economy(TokenEconomyRequest(**request_data))
        except (KeyError, TypeError, ValueError) as exc:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
        result = asdict(plan)
        result["schema"] = "raven.token_economy.v1"
        result["total_generation_budget"] = plan.total_generation_budget
        return result

    @app.post("/v1/token-economy/verification", tags=["routing"])
    async def verification_schedule(body: VerificationRequest) -> dict[str, Any]:
        try:
            spans = [VerificationSpan(**span.model_dump()) for span in body.spans]
            schedule = schedule_verification(
                spans,
                base_tokens_per_span=body.base_tokens_per_span,
                system_load=body.system_load,
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
        result = asdict(schedule)
        result["schema"] = "raven.verification_schedule.v1"
        return result

    @app.post("/v1/scientific-runs/evaluate", tags=["science"])
    async def evaluate_run(body: ScientificRunRequest, request: Request) -> dict[str, Any]:
        try:
            manifest = _build_manifest(body.manifest)
            report = evaluate_scientific_run(manifest)
        except (KeyError, TypeError, ValueError) as exc:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc

        record = {
            "schema": "raven.scientific_run.v1",
            "run_id": manifest.run_id,
            "recorded_at": _utc_now(),
            "manifest": asdict(manifest),
            "gate_report": asdict(report),
            "approvals": [],
        }
        if body.persist:
            try:
                await _store_from_request(request).save(record)
            except ValueError as exc:
                raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
        return record

    @app.get("/v1/runs", tags=["runs"])
    async def list_runs(request: Request, limit: int = 100) -> dict[str, Any]:
        limit = max(1, min(limit, 500))
        records = await _store_from_request(request).list(limit=limit)
        return {"object": "list", "data": records}

    @app.get("/v1/runs/{run_id}", tags=["runs"])
    async def get_run(run_id: str, request: Request) -> dict[str, Any]:
        try:
            record = await _store_from_request(request).get(run_id)
        except ValueError as exc:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
        if record is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "run not found")
        return record

    @app.post("/v1/runs/{run_id}/approvals", tags=["runs"])
    async def approve_run(
        run_id: str,
        body: ApprovalRequest,
        request: Request,
    ) -> dict[str, Any]:
        store = _store_from_request(request)
        try:
            record = await store.get(run_id)
        except ValueError as exc:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
        if record is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "run not found")

        approval = {
            "reviewer": body.reviewer,
            "decision": body.decision,
            "note": body.note,
            "recorded_at": _utc_now(),
        }
        record.setdefault("approvals", []).append(approval)
        record["human_decision"] = body.decision
        await store.save(record)
        return record

    return app


app = create_app()

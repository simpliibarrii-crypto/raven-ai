"""Per-tenant cost transparency — the affordability proof.

Every inference logs a CostRecord with:
- input_tokens, output_tokens
- model_family (v4-pro | v4-flash | dspark | heuristic)
- quantization (fp8 | fp16 | bf16)
- tier_id (the affordability tier that produced the inference)
- estimated_cost_usd (based on V4-Pro published pricing)
- estimated_flops (in FLOPs, derived from activated params)
- savings_vs_gpt55_usd, savings_vs_opus47_usd

Cost records are tenant-scoped. Reports are visible to the requesting
tenant ONLY — never cross-tenant. Affordability is for the patient, not
for tenant-vs-tenant comparison.

The cost equation is anchored in DeepSeek-V4-Pro's published pricing
(2026-05-22): $0.435/M input + $0.87/M output. V4-Flash is estimated
at $0.10/M + $0.30/M (verify before publishing); DSpark on-prem is $0
marginal API cost after setup.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

from runtime.affordability import (
    estimate_cost,
    estimate_flops,
    get_tier,
)

logger = logging.getLogger("openclinical.runtime.cost")


@dataclass
class CostRecord:
    """One cost record per inference.

    Created at the end of every /v1/inference call. Persisted in-memory
    (MVP) and indexed by tenant_id. Production: persist to Postgres + S3.
    """
    inference_id: str
    tenant_id: str
    psw_id: str
    model_id: str
    model_family: str  # v4-pro | v4-flash | dspark | heuristic
    tier_id: str
    quantization: str  # fp8 | fp16 | bf16
    input_tokens: int
    output_tokens: int
    activated_params_b: float
    estimated_cost_usd: float
    estimated_flops: float
    savings_vs_gpt55_usd: float
    savings_vs_opus47_usd: float
    timestamp: str
    audit_event_id: str | None = None


class CostTracker:
    """Tracks per-tenant cost records. Tenant-scoped reports only.

    Storage:
    - MVP: in-memory dict, indexed by tenant_id.
    - Production: Postgres + S3 JSONL for cold storage + analytics.
    """

    def __init__(self) -> None:
        self.records: dict[str, list[CostRecord]] = {}

    def record(self, rec: CostRecord) -> None:
        """Append a cost record to the tenant's history."""
        self.records.setdefault(rec.tenant_id, []).append(rec)
        logger.debug(
            "cost record: tenant=%s model=%s tokens=%d/%d cost=$%.6f",
            rec.tenant_id,
            rec.model_id,
            rec.input_tokens,
            rec.output_tokens,
            rec.estimated_cost_usd,
        )

    def tenant_report(
        self,
        tenant_id: str,
        since_timestamp: str | None = None,
    ) -> dict[str, Any]:
        """Per-tenant cost report — the requesting tenant ONLY.

        No cross-tenant visibility. This is by design: cost transparency
        is for the patient's affordability, not for tenant-vs-tenant
        competitive comparison.
        """
        records = self.records.get(tenant_id, [])
        if since_timestamp:
            records = [r for r in records if r.timestamp >= since_timestamp]

        if not records:
            return {
                "tenant_id": tenant_id,
                "window": {"since": since_timestamp, "until": "now"},
                "inference_count": 0,
                "totals": {
                    "estimated_cost_usd": 0.0,
                    "estimated_flops": 0.0,
                    "savings_vs_gpt55_usd": 0.0,
                    "savings_vs_opus47_usd": 0.0,
                    "input_tokens": 0,
                    "output_tokens": 0,
                },
                "by_model_family": {},
                "by_quantization": {},
                "recent_records": [],
            }

        total_cost = sum(r.estimated_cost_usd for r in records)
        total_flops = sum(r.estimated_flops for r in records)
        total_savings_gpt = sum(r.savings_vs_gpt55_usd for r in records)
        total_savings_opus = sum(r.savings_vs_opus47_usd for r in records)
        total_input = sum(r.input_tokens for r in records)
        total_output = sum(r.output_tokens for r in records)

        # Group by model family
        by_family: dict[str, dict[str, Any]] = {}
        for r in records:
            fam = r.model_family
            if fam not in by_family:
                by_family[fam] = {
                    "count": 0,
                    "cost_usd": 0.0,
                    "input_tokens": 0,
                    "output_tokens": 0,
                }
            by_family[fam]["count"] += 1
            by_family[fam]["cost_usd"] += r.estimated_cost_usd
            by_family[fam]["input_tokens"] += r.input_tokens
            by_family[fam]["output_tokens"] += r.output_tokens

        # Group by quantization
        by_quant: dict[str, dict[str, Any]] = {}
        for r in records:
            q = r.quantization
            if q not in by_quant:
                by_quant[q] = {"count": 0, "cost_usd": 0.0}
            by_quant[q]["count"] += 1
            by_quant[q]["cost_usd"] += r.estimated_cost_usd

        # Round to sane precision
        for fam in by_family.values():
            fam["cost_usd"] = round(fam["cost_usd"], 8)
        for q in by_quant.values():
            q["cost_usd"] = round(q["cost_usd"], 8)

        return {
            "tenant_id": tenant_id,
            "window": {
                "since": since_timestamp or records[0].timestamp,
                "until": records[-1].timestamp,
            },
            "inference_count": len(records),
            "totals": {
                "estimated_cost_usd": round(total_cost, 8),
                "estimated_flops": total_flops,
                "savings_vs_gpt55_usd": round(total_savings_gpt, 8),
                "savings_vs_opus47_usd": round(total_savings_opus, 8),
                "input_tokens": total_input,
                "output_tokens": total_output,
            },
            "by_model_family": by_family,
            "by_quantization": by_quant,
            "recent_records": [
                {
                    "inference_id": r.inference_id,
                    "model_id": r.model_id,
                    "model_family": r.model_family,
                    "tier_id": r.tier_id,
                    "quantization": r.quantization,
                    "input_tokens": r.input_tokens,
                    "output_tokens": r.output_tokens,
                    "estimated_cost_usd": round(r.estimated_cost_usd, 8),
                    "timestamp": r.timestamp,
                }
                for r in records[-20:]  # last 20 records
            ],
        }


def build_cost_record(
    *,
    inference_id: str,
    tenant_id: str,
    psw_id: str,
    model_id: str,
    model_family: str,
    tier_id: str,
    quantization: str,
    input_tokens: int,
    output_tokens: int,
    activated_params_b: float,
    audit_event_id: str | None = None,
) -> CostRecord:
    """Construct a CostRecord from inference parameters.

    Pricing is sourced from runtime.affordability (V4-Pro published rates).
    """
    cost = estimate_cost(tier_id, input_tokens, output_tokens)
    flops = estimate_flops(activated_params_b, input_tokens, output_tokens)

    return CostRecord(
        inference_id=inference_id,
        tenant_id=tenant_id,
        psw_id=psw_id,
        model_id=model_id,
        model_family=model_family,
        tier_id=tier_id,
        quantization=quantization,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        activated_params_b=activated_params_b,
        estimated_cost_usd=cost["tier_cost_usd"],
        estimated_flops=flops,
        savings_vs_gpt55_usd=cost["savings_vs_gpt55_usd"],
        savings_vs_opus47_usd=cost["savings_vs_opus47_usd"],
        timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        audit_event_id=audit_event_id,
    )
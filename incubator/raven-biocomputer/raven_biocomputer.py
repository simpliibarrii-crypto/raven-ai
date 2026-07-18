from __future__ import annotations

import hashlib
import json
import re
import uuid
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Mapping

_DNA_RE = re.compile(r"^[ACGTN]*$")
_SAFE_ID_RE = re.compile(r"[^a-zA-Z0-9_.-]+")
_COMPLEMENT = str.maketrans("ACGTN", "TGCAN")


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _digest(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(raw.encode()).hexdigest()


def _clean_dna(value: Any) -> str:
    if not isinstance(value, str):
        raise ValueError("sequence must be a string")
    sequence = re.sub(r"\s+", "", value).upper()
    if not sequence or not _DNA_RE.fullmatch(sequence):
        raise ValueError("sequence may contain only A, C, G, T, N and whitespace")
    return sequence


def _safe_id(value: str) -> str:
    cleaned = _SAFE_ID_RE.sub("-", value.strip()).strip("-.")
    if not cleaned:
        raise ValueError("invalid run id")
    return cleaned[:96]


@dataclass(frozen=True)
class PolicyDecision:
    allowed: bool
    level: str
    reason: str
    requires_human_review: bool = False
    matched_rules: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["matched_rules"] = list(self.matched_rules)
        return data


class BiologyPolicy:
    BLOCKED = {
        "arbitrary-shell": ("shell", "terminal", "bash", "powershell", "sudo"),
        "credential-access": ("api key", "secret token", "private key", "credential"),
        "exfiltration": ("exfiltrate", "upload private", "send patient data"),
    }
    REVIEW = {
        "clinical-decision": ("diagnose", "prescribe", "patient-specific", "medical decision"),
        "raw-phi": ("health card", "medical record number", "raw phi"),
        "wet-lab": ("run the instrument", "execute protocol", "pipetting robot"),
        "genome-editing": ("crispr", "gene drive", "genome editing"),
        "pathogen-engineering": ("increase virulence", "evade immunity", "engineer pathogen"),
    }

    def evaluate(self, task: str, tool: str, payload: Mapping[str, Any]) -> PolicyDecision:
        text = f"{task} {tool} {payload}".lower()
        blocked = tuple(k for k, terms in self.BLOCKED.items() if any(t in text for t in terms))
        if blocked:
            return PolicyDecision(
                False,
                "blocked",
                "Host, credential, or exfiltration boundary.",
                False,
                blocked,
            )
        review = tuple(k for k, terms in self.REVIEW.items() if any(t in text for t in terms))
        if review:
            return PolicyDecision(
                False,
                "human-review",
                "Qualified human review is required.",
                True,
                review,
            )
        return PolicyDecision(True, "dry-lab", "Approved for bounded local dry-lab analysis.")


class ToolRegistry:
    def list(self) -> list[dict[str, Any]]:
        return [
            {"name": "sequence_stats", "description": "DNA counts and GC fraction"},
            {"name": "reverse_complement", "description": "DNA reverse complement"},
            {"name": "find_motif", "description": "Overlapping DNA motif positions"},
            {"name": "fasta_summary", "description": "Summary for DNA FASTA records"},
        ]

    def run(self, name: str, payload: Mapping[str, Any]) -> dict[str, Any]:
        if name == "sequence_stats":
            sequence = _clean_dna(payload.get("sequence"))
            counts = Counter(sequence)
            informative = len(sequence) - counts.get("N", 0)
            gc = counts.get("G", 0) + counts.get("C", 0)
            return {
                "length": len(sequence),
                "counts": {base: counts.get(base, 0) for base in "ACGTN"},
                "gc_fraction": round(gc / informative, 6) if informative else None,
            }
        if name == "reverse_complement":
            sequence = _clean_dna(payload.get("sequence"))
            return {"sequence": sequence.translate(_COMPLEMENT)[::-1]}
        if name == "find_motif":
            sequence = _clean_dna(payload.get("sequence"))
            motif = _clean_dna(payload.get("motif"))
            positions, start = [], 0
            while (index := sequence.find(motif, start)) >= 0:
                positions.append(index)
                start = index + 1
            return {"motif": motif, "positions_zero_based": positions, "count": len(positions)}
        if name == "fasta_summary":
            text = payload.get("fasta")
            if not isinstance(text, str) or not text.strip():
                raise ValueError("fasta must be a non-empty string")
            records, header, parts = [], None, []

            def flush() -> None:
                nonlocal header, parts
                if header is None:
                    return
                sequence = _clean_dna("".join(parts))
                records.append({"id": header.split()[0], "length": len(sequence)})

            for raw in text.splitlines():
                line = raw.strip()
                if not line:
                    continue
                if line.startswith(">"):
                    flush()
                    header, parts = line[1:].strip(), []
                else:
                    if header is None:
                        raise ValueError("FASTA sequence appeared before a header")
                    parts.append(line)
            flush()
            if not records:
                raise ValueError("no FASTA records found")
            return {"record_count": len(records), "records": records}
        raise KeyError(f"unknown tool: {name}")


class BioComputer:
    def __init__(self, workspace_root: str | Path = "runs") -> None:
        self.root = Path(workspace_root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.policy = BiologyPolicy()
        self.tools = ToolRegistry()

    def execute(
        self,
        *,
        task: str,
        tool: str,
        payload: Mapping[str, Any],
        run_id: str | None = None,
    ) -> dict[str, Any]:
        run_id = _safe_id(run_id or f"run-{uuid.uuid4().hex[:12]}")
        run_dir = (self.root / run_id).resolve()
        if self.root.resolve() not in run_dir.parents:
            raise ValueError("workspace escape rejected")
        run_dir.mkdir(exist_ok=False)
        decision = self.policy.evaluate(task, tool, payload)
        receipt: dict[str, Any] = {
            "schema": "raven.biocomputer.run.v1",
            "run_id": run_id,
            "task": task,
            "tool": tool,
            "status": "blocked" if not decision.allowed else "running",
            "started_at": _now(),
            "completed_at": None,
            "policy": decision.to_dict(),
            "input_digest": _digest(dict(payload)),
            "result": {},
            "error": None,
        }
        (run_dir / "input.json").write_text(json.dumps(dict(payload), indent=2) + "\n")
        if decision.allowed:
            try:
                receipt["result"] = self.tools.run(tool, payload)
                receipt["status"] = "completed"
                (run_dir / "result.json").write_text(
                    json.dumps(receipt["result"], indent=2) + "\n"
                )
            except Exception as exc:
                receipt["status"] = "failed"
                receipt["error"] = f"{type(exc).__name__}: {exc}"
        receipt["completed_at"] = _now()
        receipt["integrations"] = {
            "raven_evidence_graph": {
                "schema": "raven.evidence_graph.v1",
                "run_id": run_id,
            },
            "jspace_envelope": {
                "schema": "jspace.chain.envelope.v1",
                "workspace": "raven-biocomputer",
                "policy_gate": decision.to_dict(),
            },
            "home_for_ai": {
                "schema": "home.raven_run_record.v1",
                "surface": "raven-biocomputer",
                "replayable": receipt["status"] == "completed",
            },
            "hermes_edge": {
                "schema": "hermes.edge.task.v1",
                "preferred_route": "deterministic-tool-first",
                "cloud_required": False,
            },
            "openclinical_ai": {
                "schema": "openclinical.biocomputer.bridge.v1",
                "clinical_use": False,
                "human_review_required": decision.requires_human_review,
            },
        }
        (run_dir / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
        return receipt

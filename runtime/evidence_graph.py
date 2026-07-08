"""Raven Evidence Graph core.

The graph is intentionally dependency-free so it can run inside Raven AI,
OpenClinical AI, Home for AI, Hermes Edge, hosted demos, and edge devices.
It tracks sources, claims, entity mentions, confidence, risk, and provenance
without pretending to perform clinical validation by itself.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import hashlib
import json
import re
from typing import Any, Iterable


_WORD_RE = re.compile(r"[A-Za-z][A-Za-z0-9_-]{2,}")
_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")


@dataclass(frozen=True)
class EvidenceSource:
    """A source that can support or challenge claims."""

    id: str
    title: str
    kind: str
    uri: str | None = None
    retrieved_at: str | None = None
    quality: float = 0.5
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class EvidenceClaim:
    """A claim extracted from a source or produced by an agent."""

    id: str
    text: str
    source_ids: tuple[str, ...] = ()
    confidence: float = 0.5
    risk: str = "medium"
    labels: tuple[str, ...] = ()
    entities: tuple[str, ...] = ()
    created_at: str | None = None


@dataclass(frozen=True)
class EvidenceEdge:
    """A relationship between two graph objects."""

    source_id: str
    target_id: str
    relation: str
    weight: float = 1.0


@dataclass(frozen=True)
class EvidenceTrace:
    """A compact provenance packet for an agent output."""

    answer: str
    claim_ids: tuple[str, ...]
    source_ids: tuple[str, ...]
    confidence: float
    risk: str
    explanation: str


class EvidenceGraph:
    """In-memory evidence graph with deterministic scoring and export."""

    def __init__(self) -> None:
        self.sources: dict[str, EvidenceSource] = {}
        self.claims: dict[str, EvidenceClaim] = {}
        self.edges: list[EvidenceEdge] = []

    def add_source(
        self,
        title: str,
        kind: str,
        uri: str | None = None,
        quality: float = 0.5,
        metadata: dict[str, Any] | None = None,
        source_id: str | None = None,
    ) -> EvidenceSource:
        """Add or replace an evidence source."""
        sid = source_id or stable_id("src", title, kind, uri or "")
        source = EvidenceSource(
            id=sid,
            title=title.strip(),
            kind=kind.strip().lower(),
            uri=uri,
            retrieved_at=utc_now(),
            quality=clamp(quality),
            metadata=metadata or {},
        )
        self.sources[source.id] = source
        return source

    def add_claim(
        self,
        text: str,
        source_ids: Iterable[str] = (),
        confidence: float = 0.5,
        risk: str = "medium",
        labels: Iterable[str] = (),
        entities: Iterable[str] | None = None,
        claim_id: str | None = None,
    ) -> EvidenceClaim:
        """Add or replace a claim and link it to source ids."""
        normalized_text = normalize_space(text)
        clean_source_ids = tuple(dict.fromkeys(source_ids))
        claim = EvidenceClaim(
            id=claim_id or stable_id("claim", normalized_text, *clean_source_ids),
            text=normalized_text,
            source_ids=clean_source_ids,
            confidence=clamp(confidence),
            risk=normalize_risk(risk),
            labels=tuple(dict.fromkeys(label.strip().lower() for label in labels if label.strip())),
            entities=tuple(entities if entities is not None else extract_entities(normalized_text)),
            created_at=utc_now(),
        )
        self.claims[claim.id] = claim
        for source_id in claim.source_ids:
            self.link(source_id, claim.id, "supports", weight=claim.confidence)
        return claim

    def ingest_document(
        self,
        title: str,
        text: str,
        kind: str = "document",
        uri: str | None = None,
        quality: float = 0.5,
        labels: Iterable[str] = (),
        max_claims: int = 12,
    ) -> list[EvidenceClaim]:
        """Create one source and sentence-level claims from a document."""
        source = self.add_source(title=title, kind=kind, uri=uri, quality=quality)
        sentences = split_claims(text)[:max_claims]
        claims: list[EvidenceClaim] = []
        for sentence in sentences:
            confidence = source.quality * evidence_density(sentence)
            claims.append(
                self.add_claim(
                    sentence,
                    source_ids=[source.id],
                    confidence=confidence,
                    risk=infer_risk(sentence),
                    labels=labels,
                )
            )
        return claims

    def link(self, source_id: str, target_id: str, relation: str, weight: float = 1.0) -> EvidenceEdge:
        """Create a relation edge between two nodes."""
        edge = EvidenceEdge(
            source_id=source_id,
            target_id=target_id,
            relation=relation.strip().lower(),
            weight=clamp(weight),
        )
        if edge not in self.edges:
            self.edges.append(edge)
        return edge

    def explain_claim(self, claim_id: str) -> dict[str, Any]:
        """Return a source-backed explanation packet for one claim."""
        claim = self.claims[claim_id]
        sources = [self.sources[sid] for sid in claim.source_ids if sid in self.sources]
        score = self.score_claim(claim_id)
        return {
            "claim": asdict(claim),
            "sources": [asdict(source) for source in sources],
            "score": score,
            "risk": claim.risk,
            "explanation": explain_score(claim, sources, score),
        }

    def score_claim(self, claim_id: str) -> float:
        """Score a claim from confidence, source quality, and risk penalty."""
        claim = self.claims[claim_id]
        source_scores = [self.sources[sid].quality for sid in claim.source_ids if sid in self.sources]
        source_quality = sum(source_scores) / len(source_scores) if source_scores else 0.25
        penalty = {"low": 1.0, "medium": 0.82, "high": 0.62, "critical": 0.42}[claim.risk]
        return round(clamp((claim.confidence * 0.55 + source_quality * 0.45) * penalty), 3)

    def trace_answer(self, answer: str, claim_ids: Iterable[str]) -> EvidenceTrace:
        """Build a provenance trace for an agent answer."""
        ids = tuple(cid for cid in claim_ids if cid in self.claims)
        source_ids: list[str] = []
        scores: list[float] = []
        risks: list[str] = []
        for cid in ids:
            claim = self.claims[cid]
            scores.append(self.score_claim(cid))
            risks.append(claim.risk)
            source_ids.extend(claim.source_ids)
        confidence = round(sum(scores) / len(scores), 3) if scores else 0.0
        risk = highest_risk(risks)
        explanation = (
            f"Trace uses {len(ids)} claim(s) across {len(set(source_ids))} source(s); "
            f"aggregate confidence {confidence}."
        )
        return EvidenceTrace(
            answer=normalize_space(answer),
            claim_ids=ids,
            source_ids=tuple(dict.fromkeys(source_ids)),
            confidence=confidence,
            risk=risk,
            explanation=explanation,
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize the graph into a JSON-compatible dict."""
        return {
            "schema": "raven.evidence_graph.v1",
            "sources": [asdict(source) for source in self.sources.values()],
            "claims": [asdict(claim) for claim in self.claims.values()],
            "edges": [asdict(edge) for edge in self.edges],
        }

    def to_json(self) -> str:
        """Serialize the graph as stable, sorted JSON."""
        return json.dumps(self.to_dict(), indent=2, sort_keys=True)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "EvidenceGraph":
        """Load an EvidenceGraph from a dict produced by to_dict."""
        graph = cls()
        for raw in payload.get("sources", []):
            graph.sources[raw["id"]] = EvidenceSource(**raw)
        for raw in payload.get("claims", []):
            raw = dict(raw)
            raw["source_ids"] = tuple(raw.get("source_ids", ()))
            raw["labels"] = tuple(raw.get("labels", ()))
            raw["entities"] = tuple(raw.get("entities", ()))
            graph.claims[raw["id"]] = EvidenceClaim(**raw)
        for raw in payload.get("edges", []):
            graph.edges.append(EvidenceEdge(**raw))
        return graph

    @classmethod
    def from_json(cls, payload: str) -> "EvidenceGraph":
        """Load an EvidenceGraph from JSON."""
        return cls.from_dict(json.loads(payload))


def split_claims(text: str) -> list[str]:
    """Split plain text into concise claim-like sentences."""
    chunks = [normalize_space(part) for part in _SENTENCE_RE.split(text.replace("\n", " "))]
    return [chunk for chunk in chunks if len(chunk) >= 18]


def extract_entities(text: str, limit: int = 12) -> list[str]:
    """Extract simple deterministic entity candidates."""
    stopwords = {
        "and",
        "are",
        "can",
        "for",
        "from",
        "into",
        "that",
        "the",
        "this",
        "with",
        "without",
    }
    entities: list[str] = []
    for match in _WORD_RE.findall(text):
        token = match.strip("-_ ")
        if token.lower() in stopwords:
            continue
        if token[0].isupper() or token.lower() in domain_terms():
            entities.append(token)
    return list(dict.fromkeys(entities))[:limit]


def evidence_density(text: str) -> float:
    """Heuristic confidence seed based on evidence-like details."""
    tokens = _WORD_RE.findall(text)
    if not tokens:
        return 0.2
    number_bonus = 0.15 if re.search(r"\d", text) else 0.0
    entity_bonus = min(len(extract_entities(text)) * 0.03, 0.18)
    length_bonus = min(len(tokens) / 80, 0.25)
    return clamp(0.45 + number_bonus + entity_bonus + length_bonus)


def infer_risk(text: str) -> str:
    """Infer a conservative risk tier from claim text."""
    lowered = text.lower()
    if any(term in lowered for term in ("diagnosis", "dose", "treatment", "patient", "phi", "consent")):
        return "high"
    if any(term in lowered for term in ("clinical", "medical", "genomic", "biology", "healthcare")):
        return "medium"
    return "low"


def explain_score(claim: EvidenceClaim, sources: list[EvidenceSource], score: float) -> str:
    """Human-readable explanation for a score."""
    if not sources:
        return f"Claim has no linked source; confidence is limited to {score}."
    titles = ", ".join(source.title for source in sources[:3])
    return f"Claim is linked to {len(sources)} source(s): {titles}. Risk tier is {claim.risk}; score is {score}."


def highest_risk(risks: Iterable[str]) -> str:
    """Return the highest risk tier from an iterable."""
    order = {"low": 0, "medium": 1, "high": 2, "critical": 3}
    chosen = "low"
    for risk in risks:
        normalized = normalize_risk(risk)
        if order[normalized] > order[chosen]:
            chosen = normalized
    return chosen


def normalize_risk(risk: str) -> str:
    """Normalize risk into the supported tier set."""
    normalized = risk.strip().lower()
    return normalized if normalized in {"low", "medium", "high", "critical"} else "medium"


def normalize_space(text: str) -> str:
    """Collapse whitespace without changing meaning."""
    return re.sub(r"\s+", " ", text).strip()


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    """Clamp a float into the scoring range."""
    return max(low, min(high, float(value)))


def stable_id(prefix: str, *parts: str) -> str:
    """Create stable ids for deterministic tests and repeat imports."""
    digest = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:16]
    return f"{prefix}_{digest}"


def utc_now() -> str:
    """Current UTC timestamp in ISO-8601 format."""
    return datetime.now(timezone.utc).isoformat()


def domain_terms() -> set[str]:
    """Domain words that should survive simple entity extraction."""
    return {
        "agent",
        "agents",
        "audit",
        "biology",
        "clinical",
        "consent",
        "evidence",
        "genomic",
        "healthcare",
        "local-first",
        "model",
        "provenance",
        "tenant",
        "workflow",
    }

"""Model registry + model adapters.

The registry stores signed model manifests with:
- Model id, version, type
- SHA-256 of the model artifact
- Signature (Ed25519) of the manifest
- Model card (clinical + technical metadata)

Adapters run inference. MVP uses heuristic adapters (no real ML yet) to
prove the architecture. Real biology + clinical models plug in via adapters.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from nacl.signing import VerifyKey
from nacl.exceptions import BadSignatureError

logger = logging.getLogger("openclinical.runtime.models")


# -- harness system prompt ---------------------------------------------------


_HARNESS_PROMPT: str | None = None
_HARNESS_PATH: Path | None = None


def load_harness_prompt(docs_dir: Path) -> str:
    """Load the AI governance harness system prompt from docs/CLAUDE.md.

    This prompt is injected into every inference call via adapters.
    It encodes the factual accuracy mandate, anti-mandates, and
    audience (healthcare practitioners) configuration.

    Returns the prompt text. Uses a module-level cache so it's
    loaded once and reused. If the file doesn't exist, returns
    a minimal fallback.
    """
    global _HARNESS_PROMPT, _HARNESS_PATH
    path = docs_dir / "CLAUDE.md"
    if _HARNESS_PROMPT is not None and _HARNESS_PATH == path:
        return _HARNESS_PROMPT

    if path.exists():
        _HARNESS_PROMPT = path.read_text()
        _HARNESS_PATH = path
        logger.info("loaded harness system prompt from %s (%d chars)", path, len(_HARNESS_PROMPT))
        return _HARNESS_PROMPT

    logger.warning("harness prompt not found at %s — using fallback", path)
    _HARNESS_PROMPT = (
        "You are openclinical-ai. You serve healthcare practitioners. "
        "Provide factual, unfiltered information. Do not add medical disclaimers. "
        "Cite sources when available. Be honest about uncertainty."
    )
    _HARNESS_PATH = path
    return _HARNESS_PROMPT


class ModelSignatureError(Exception):
    """Raised when a model's signature is invalid or missing."""
    pass


@dataclass
class ModelCard:
    """Clinical + technical metadata for a model.

    See MODEL-CARD-SCHEMA.md for the full schema.
    """
    id: str
    version: str
    model_type: str
    description: str
    intended_use: str
    training_data: str
    evaluation_metrics: dict[str, Any] = field(default_factory=dict)
    ethical_considerations: str = ""
    clinical_validation: str = ""
    phipa_compliance: str = ""
    license: str = "Apache-2.0"


@dataclass
class LoadedModel:
    """A model loaded into memory and ready to run inference."""
    id: str
    version: str
    model_type: str
    description: str
    card: ModelCard
    loaded_at: str
    adapter: "ModelAdapter"

    async def run(self, inputs: dict[str, Any]) -> dict[str, Any]:
        """Delegate inference to the adapter."""
        return await self.adapter.run(inputs)


class ModelAdapter:
    """Base class for model adapters.

    Each model type implements its own adapter. Adapters are pluggable so
    real biology + clinical models can be swapped in.

    system_prompt is the governance harness from docs/CLAUDE.md — injected
    into every inference call when using real LLMs. Heuristic adapters
    (like PSWShiftHandoffAdapter) ignore it, but it's available for any
    adapter that makes real model calls.
    """

    def __init__(self, system_prompt: str | None = None) -> None:
        self.system_prompt = system_prompt

    async def run(self, inputs: dict[str, Any]) -> dict[str, Any]:
        """Run inference. Override in subclasses."""
        raise NotImplementedError


class PSWShiftHandoffAdapter(ModelAdapter):
    """Heuristic PSW shift-handoff adapter for MVP.

    Captures structured shift handoff notes:
    - vitals (BP, HR, temp, SpO2)
    - mobility (ambulation, transfers, falls)
    - intake (food, fluid)
    - output (urine, BM)
    - mood (alert, confused, agitated, calm)
    - incidents
    - family contact events

    MVP uses simple heuristics — no real ML yet. This proves the
    architecture: registry → consent → audit → output.

    Real PSW AI will replace this with a fine-tuned clinical LLM or
    a multi-modal model trained on anonymized PSW shift notes.
    """

    def __init__(self, system_prompt: str | None = None) -> None:
        super().__init__(system_prompt=system_prompt)

    async def run(self, inputs: dict[str, Any]) -> dict[str, Any]:
        """Process PSW shift handoff inputs."""
        notes = inputs.get("notes", "")
        observations = inputs.get("observations", {})
        timestamp = inputs.get("timestamp", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
        psw_id = inputs.get("psw_id", "unknown")

        # Heuristic categorization of free-text notes
        categorized = _categorize_notes(notes)

        # Structure observations
        structured_obs = _structure_observations(observations)

        # Detect potential concerns (heuristic)
        concerns = _detect_concerns(structured_obs, categorized)

        # Generate handoff summary
        summary = _generate_summary(structured_obs, categorized, concerns)

        return {
            "shift_handoff": {
                "psw_id": psw_id,
                "timestamp": timestamp,
                "resident_id": inputs.get("resident_id"),
                "raw_notes": notes,
                "categorized_notes": categorized,
                "structured_observations": structured_obs,
                "concerns": concerns,
                "summary": summary,
                "followup_required": any(c["severity"] in ("medium", "high") for c in concerns),
            }
        }


def _categorize_notes(notes: str) -> dict[str, list[str]]:
    """Heuristic categorization of free-text PSW notes."""
    notes_lower = notes.lower()
    categorized: dict[str, list[str]] = {
        "vitals": [],
        "mobility": [],
        "mood": [],
        "intake": [],
        "output": [],
        "incidents": [],
        "family": [],
        "medications": [],
        "general": [],
    }

    if any(w in notes_lower for w in ["bp", "blood pressure", "heart rate", "temp", "spo2"]):
        categorized["vitals"].append(notes)
    if any(w in notes_lower for w in ["walked", "ambulated", "transfer", "fall", "mobility"]):
        categorized["mobility"].append(notes)
    if any(w in notes_lower for w in ["confused", "agitated", "calm", "alert", "anxious", "upset", "happy"]):
        categorized["mood"].append(notes)
    if any(w in notes_lower for w in ["ate", "drank", "fluid", "meal", "breakfast", "lunch", "dinner", "snack"]):
        categorized["intake"].append(notes)
    if any(w in notes_lower for w in ["voided", "bm", "bowel", "urine", "incontinent"]):
        categorized["output"].append(notes)
    if any(w in notes_lower for w in ["incident", "fell", "fall", "injury", "wound", "skin tear"]):
        categorized["incidents"].append(notes)
    if any(w in notes_lower for w in ["family", "daughter", "son", "spouse", "visited", "called"]):
        categorized["family"].append(notes)
    if any(w in notes_lower for w in ["med", "medication", "refused", "took", "as needed", "prn"]):
        categorized["medications"].append(notes)
    if not any(categorized[k] for k in categorized if k != "general"):
        categorized["general"].append(notes)

    return {k: v for k, v in categorized.items() if v}


def _structure_observations(observations: dict[str, Any]) -> dict[str, Any]:
    """Structure clinical observations into FHIR-like format."""
    return {
        "vitals": {
            "bp": observations.get("bp"),
            "hr": observations.get("hr"),
            "temp_c": observations.get("temp_c"),
            "spo2": observations.get("spo2"),
            "pain": observations.get("pain"),
        },
        "mobility": {
            "ambulation": observations.get("ambulation"),
            "transfers": observations.get("transfers"),
            "fall_risk": observations.get("fall_risk"),
        },
        "intake": {
            "meal_pct": observations.get("meal_pct"),
            "fluid_ml": observations.get("fluid_ml"),
        },
        "output": {
            "voids": observations.get("voids"),
            "bm": observations.get("bm"),
        },
        "mood": observations.get("mood"),
        "skin": observations.get("skin"),
    }


def _detect_concerns(
    observations: dict[str, Any],
    categorized: dict[str, list[str]],
) -> list[dict[str, str]]:
    """Detect potential clinical concerns (heuristic for MVP)."""
    concerns = []

    vitals = observations.get("vitals", {})
    if vitals.get("bp"):
        try:
            systolic = int(str(vitals["bp"]).split("/")[0])
            if systolic > 160 or systolic < 90:
                concerns.append({
                    "type": "vitals",
                    "severity": "high" if systolic > 180 or systolic < 80 else "medium",
                    "detail": f"BP {vitals['bp']} outside normal range",
                })
        except (ValueError, IndexError):
            pass

    if vitals.get("hr"):
        try:
            hr = int(vitals["hr"])
            if hr > 110 or hr < 50:
                concerns.append({
                    "type": "vitals",
                    "severity": "high" if hr > 130 or hr < 40 else "medium",
                    "detail": f"HR {hr} outside normal range",
                })
        except ValueError:
            pass

    if vitals.get("temp_c"):
        try:
            temp = float(vitals["temp_c"])
            if temp >= 38.0 or temp <= 35.5:
                concerns.append({
                    "type": "vitals",
                    "severity": "high" if temp >= 39.0 or temp <= 35.0 else "medium",
                    "detail": f"Temp {temp}°C outside normal range",
                })
        except ValueError:
            pass

    if vitals.get("spo2"):
        try:
            spo2 = int(str(vitals["spo2"]).rstrip("%"))
            if spo2 < 92:
                concerns.append({
                    "type": "vitals",
                    "severity": "high" if spo2 < 88 else "medium",
                    "detail": f"SpO2 {spo2}% below normal",
                })
        except ValueError:
            pass

    if categorized.get("incidents"):
        concerns.append({
            "type": "incident",
            "severity": "high",
            "detail": "Incident reported in shift notes — review required",
        })

    return concerns


def _generate_summary(
    observations: dict[str, Any],
    categorized: dict[str, list[str]],
    concerns: list[dict[str, str]],
) -> str:
    """Generate a structured shift handoff summary."""
    parts = []

    vitals = observations.get("vitals", {})
    vital_parts = []
    if vitals.get("bp"):
        vital_parts.append(f"BP {vitals['bp']}")
    if vitals.get("hr"):
        vital_parts.append(f"HR {vitals['hr']}")
    if vitals.get("temp_c"):
        vital_parts.append(f"Temp {vitals['temp_c']}°C")
    if vitals.get("spo2"):
        spo2_str = str(vitals["spo2"])
        spo2_display = spo2_str if spo2_str.endswith("%") else f"{spo2_str}%"
        vital_parts.append(f"SpO2 {spo2_display}")
    if vital_parts:
        parts.append("Vitals: " + ", ".join(vital_parts))

    if observations.get("mobility", {}).get("ambulation"):
        parts.append(f"Mobility: {observations['mobility']['ambulation']}")

    if observations.get("intake", {}).get("meal_pct") is not None:
        parts.append(f"Meal: {observations['intake']['meal_pct']}%")

    if observations.get("mood"):
        parts.append(f"Mood: {observations['mood']}")

    if concerns:
        parts.append(
            "Concerns: " + "; ".join(f"{c['type']} ({c['severity']})" for c in concerns)
        )

    if not parts:
        return "Shift documented. No specific observations noted."

    return "Shift handoff summary: " + ". ".join(parts) + "."


class ModelRegistry:
    """Registry of signed models."""

    def __init__(self, registry_path: Path, system_prompt: str | None = None) -> None:
        self.registry_path = registry_path
        self.registry_path.mkdir(parents=True, exist_ok=True)
        self.loaded_models: dict[str, LoadedModel] = {}
        self.signing_keys: dict[str, VerifyKey] = {}
        self.system_prompt = system_prompt

    async def load_all(self) -> int:
        """Load all signed models from the registry path."""
        count = 0
        for manifest_path in self.registry_path.glob("*.manifest.json"):
            try:
                await self._load_manifest(manifest_path)
                count += 1
            except Exception as e:
                logger.warning("failed to load model from %s: %s", manifest_path, e)
        return count

    async def _load_manifest(self, manifest_path: Path) -> None:
        """Load and verify a single model manifest."""
        with open(manifest_path) as f:
            manifest = json.load(f)

        # Verify signature
        signature = manifest.pop("signature", None)
        if not signature:
            raise ModelSignatureError(f"Manifest {manifest_path} has no signature")

        key_id = signature["key_id"]
        signature_bytes = bytes.fromhex(signature["value"])

        if key_id not in self.signing_keys:
            # Look up the public key
            key_path = self.registry_path / "keys" / f"{key_id}.pub"
            if not key_path.exists():
                raise ModelSignatureError(f"No public key for {key_id}")
            key_bytes = bytes.fromhex(key_path.read_text().strip())
            if len(key_bytes) != 32:
                raise ModelSignatureError(
                    f"Public key {key_id} is {len(key_bytes)} bytes, expected 32"
                )
            self.signing_keys[key_id] = VerifyKey(key_bytes)

        verify_key = self.signing_keys[key_id]

        # Manifest bytes (must match what was signed)
        manifest_bytes = json.dumps(manifest, sort_keys=True).encode()

        try:
            verify_key.verify(manifest_bytes, signature_bytes)
        except BadSignatureError:
            raise ModelSignatureError(f"Invalid signature for {manifest_path}")

        # Load the model
        model_id = manifest["id"]
        model_version = manifest["version"]
        model_type = manifest["model_type"]

        # MVP: heuristic adapter for PSW shift handoff
        if model_id == "psw-shift-handoff":
            adapter = PSWShiftHandoffAdapter(system_prompt=self.system_prompt)
        else:
            logger.warning("no adapter for model type %s — loading as passthrough", model_type)
            adapter = PSWShiftHandoffAdapter(system_prompt=self.system_prompt)  # MVP fallback

        card = ModelCard(**manifest.get("card", {}))

        self.loaded_models[model_id] = LoadedModel(
            id=model_id,
            version=model_version,
            model_type=model_type,
            description=manifest.get("description", ""),
            card=card,
            loaded_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            adapter=adapter,
        )
        logger.info("loaded model %s v%s", model_id, model_version)

    def get(self, model_id: str) -> LoadedModel | None:
        """Get a loaded model by ID."""
        return self.loaded_models.get(model_id)
"""Tests for the openclinical-ai substrate MVP.

Run with:
    python3 -m pytest tests/
"""
from __future__ import annotations

import asyncio
import json
import sys
import tempfile
from pathlib import Path

import pytest

# Add parent dir to path so we can import runtime modules
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from runtime.config import Settings
from runtime.audit import AuditLogger
from runtime.consent import ConsentEngine, ConsentDenied
from runtime.models import (
    LoadedModel,
    ModelCard,
    ModelRegistry,
    ModelSignatureError,
    PSWShiftHandoffAdapter,
    _categorize_notes,
    _detect_concerns,
    _structure_observations,
)


@pytest.fixture
def tmp_paths():
    """Temp directories for registry/audit/consent."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        yield {
            "registry": tmp / "registry",
            "audit": tmp / "audit",
            "consent": tmp / "consent",
        }


# -- audit --------------------------------------------------------------------


@pytest.mark.asyncio
async def test_audit_log_and_query(tmp_paths):
    audit = AuditLogger(audit_path=tmp_paths["audit"])
    eid = await audit.log(
        event_type="inference",
        patient_id="p1",
        model_id="m1",
        model_version="1.0",
        consent_token="tok",
    )
    assert eid
    events = await audit.query(patient_id="p1")
    assert len(events) == 1
    assert events[0]["event_type"] == "inference"


@pytest.mark.asyncio
async def test_audit_query_filtered(tmp_paths):
    audit = AuditLogger(audit_path=tmp_paths["audit"])
    await audit.log(event_type="inference", patient_id="p1", model_id="m1")
    await audit.log(event_type="inference", patient_id="p2", model_id="m1")
    p1_events = await audit.query(patient_id="p1")
    assert len(p1_events) == 1
    assert p1_events[0]["patient_id"] == "p1"


# -- consent ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_consent_default_denied(tmp_paths):
    engine = ConsentEngine(consent_path=tmp_paths["consent"])
    with pytest.raises(ConsentDenied):
        await engine.check("p1", "m1")


@pytest.mark.asyncio
async def test_consent_granted(tmp_paths):
    engine = ConsentEngine(consent_path=tmp_paths["consent"])
    token = await engine.grant_consent("p1", ["*"], "psw-brian")
    assert token
    await engine.check("p1", "m1", consent_token=token)  # should not raise


@pytest.mark.asyncio
async def test_consent_revoked(tmp_paths):
    engine = ConsentEngine(consent_path=tmp_paths["consent"])
    await engine.grant_consent("p1", ["*"], "psw-brian")
    await engine.revoke_consent("p1", "psw-brian")
    with pytest.raises(ConsentDenied):
        await engine.check("p1", "m1")


@pytest.mark.asyncio
async def test_consent_scope_limited(tmp_paths):
    engine = ConsentEngine(consent_path=tmp_paths["consent"])
    token = await engine.grant_consent("p1", ["psw-shift-handoff"], "psw-brian")
    await engine.check("p1", "psw-shift-handoff", consent_token=token)  # ok
    with pytest.raises(ConsentDenied):
        await engine.check("p1", "biology-protein-fold", consent_token=token)


# -- PSW adapter --------------------------------------------------------------


@pytest.mark.asyncio
async def test_psw_adapter_basic():
    adapter = PSWShiftHandoffAdapter()
    out = await adapter.run({
        "notes": "BP 145/90, walked 20m, calm mood, daughter visited, refused meds",
        "observations": {"bp": "145/90", "hr": "78", "ambulation": "walked 20m", "mood": "calm"},
        "resident_id": "r1",
        "psw_id": "psw-brian",
    })
    h = out["shift_handoff"]
    assert h["psw_id"] == "psw-brian"
    assert h["resident_id"] == "r1"
    assert "Vitals" in h["summary"]
    assert h["structured_observations"]["vitals"]["bp"] == "145/90"


@pytest.mark.asyncio
async def test_psw_adapter_high_bp_concern():
    out = await PSWShiftHandoffAdapter().run({
        "notes": "BP 195/110",
        "observations": {"bp": "195/110"},
        "resident_id": "r1",
        "psw_id": "psw-brian",
    })
    concerns = out["shift_handoff"]["concerns"]
    assert len(concerns) >= 1
    assert any(c["type"] == "vitals" and c["severity"] in ("medium", "high") for c in concerns)


@pytest.mark.asyncio
async def test_psw_adapter_low_spo2_concern():
    out = await PSWShiftHandoffAdapter().run({
        "notes": "SpO2 85% on room air",
        "observations": {"spo2": "85%"},
        "resident_id": "r1",
        "psw_id": "psw-brian",
    })
    concerns = out["shift_handoff"]["concerns"]
    assert any(c["type"] == "vitals" and c["severity"] == "high" for c in concerns)


@pytest.mark.asyncio
async def test_psw_adapter_incident_concern():
    out = await PSWShiftHandoffAdapter().run({
        "notes": "Resident had a fall in the bathroom",
        "observations": {},
        "resident_id": "r1",
        "psw_id": "psw-brian",
    })
    concerns = out["shift_handoff"]["concerns"]
    assert any(c["type"] == "incident" for c in concerns)
    assert out["shift_handoff"]["followup_required"] is True


# -- heuristic helpers --------------------------------------------------------


def test_categorize_vitals():
    cats = _categorize_notes("BP 145/90 and HR 78")
    assert "vitals" in cats


def test_categorize_mobility():
    cats = _categorize_notes("Walked 20m with walker")
    assert "mobility" in cats


def test_categorize_mood():
    cats = _categorize_notes("Resident was agitated and confused")
    assert "mood" in cats


def test_categorize_general_fallback():
    cats = _categorize_notes("Random notes that match nothing specific")
    assert "general" in cats


def test_structure_observations():
    obs = _structure_observations({"bp": "120/80", "hr": "72", "ambulation": "walked 10m"})
    assert obs["vitals"]["bp"] == "120/80"
    assert obs["vitals"]["hr"] == "72"
    assert obs["mobility"]["ambulation"] == "walked 10m"


def test_detect_concerns_temp_high():
    concerns = _detect_concerns(_structure_observations({"temp_c": "39.5"}), {})
    assert any("Temp" in c["detail"] for c in concerns)


# -- model registry -----------------------------------------------------------


@pytest.mark.asyncio
async def test_model_registry_signature_required(tmp_paths):
    """Unsigned manifest must be rejected."""
    registry_dir = tmp_paths["registry"]
    registry_dir.mkdir(parents=True, exist_ok=True)
    (registry_dir / "bad.manifest.json").write_text(json.dumps({
        "id": "bad-model",
        "version": "1.0.0",
        "model_type": "test",
        "description": "no signature",
        # no signature field!
    }))

    registry = ModelRegistry(registry_path=registry_dir)
    # load_all should silently skip — but no model loaded
    count = await registry.load_all()
    assert count == 0
    assert len(registry.loaded_models) == 0


@pytest.mark.asyncio
async def test_model_registry_signature_invalid(tmp_paths):
    """Tampered manifest must be rejected."""
    registry_dir = tmp_paths["registry"]
    keys_dir = registry_dir / "keys"
    keys_dir.mkdir(parents=True, exist_ok=True)

    from nacl.signing import SigningKey
    sk = SigningKey.generate()
    keys_dir.joinpath("default.pub").write_text(bytes(sk.verify_key).hex())

    # Manifest with bogus signature
    manifest = {
        "id": "tampered",
        "version": "1.0.0",
        "model_type": "test",
        "description": "tampered",
        "signature": {
            "key_id": "default",
            "algorithm": "ed25519",
            "value": "00" * 64,  # bogus
        },
    }
    (registry_dir / "tampered.manifest.json").write_text(json.dumps(manifest))

    registry = ModelRegistry(registry_path=registry_dir)
    count = await registry.load_all()
    assert count == 0


@pytest.mark.asyncio
async def test_model_registry_signed_manifest_loads(tmp_paths):
    """A correctly-signed manifest should load successfully."""
    from nacl.signing import SigningKey

    registry_dir = tmp_paths["registry"]
    keys_dir = registry_dir / "keys"
    keys_dir.mkdir(parents=True, exist_ok=True)

    sk = SigningKey.generate()
    keys_dir.joinpath("default.pub").write_text(bytes(sk.verify_key).hex())

    manifest = {
        "id": "psw-shift-handoff",
        "version": "1.0.0",
        "model_type": "clinical-heuristic",
        "description": "test",
        "card": {
            "id": "psw-shift-handoff",
            "version": "1.0.0",
            "model_type": "clinical-heuristic",
            "description": "test",
            "intended_use": "test",
            "training_data": "test",
            "evaluation_metrics": {},
            "ethical_considerations": "",
            "clinical_validation": "",
            "phipa_compliance": "",
            "license": "Apache-2.0",
        },
        "artifact_sha256": "00" * 32,
        "artifact_size_bytes": 0,
        "created_at": "2026-06-29T00:00:00Z",
    }
    canonical = json.dumps(manifest, sort_keys=True).encode()
    sig = sk.sign(canonical).signature
    manifest["signature"] = {"key_id": "default", "algorithm": "ed25519", "value": sig.hex()}
    (registry_dir / "psw-shift-handoff.v1.0.0.manifest.json").write_text(json.dumps(manifest))

    registry = ModelRegistry(registry_path=registry_dir)
    count = await registry.load_all()
    assert count == 1
    model = registry.get("psw-shift-handoff")
    assert model is not None
    assert model.version == "1.0.0"


# -- end-to-end through server -------------------------------------------------


@pytest.mark.asyncio
async def test_full_inference_flow(tmp_paths):
    """End-to-end: signed manifest → consent → inference → audit."""
    from nacl.signing import SigningKey

    # Set up registry with signed manifest
    registry_dir = tmp_paths["registry"]
    keys_dir = registry_dir / "keys"
    keys_dir.mkdir(parents=True, exist_ok=True)
    sk = SigningKey.generate()
    keys_dir.joinpath("default.pub").write_text(bytes(sk.verify_key).hex())

    manifest = {
        "id": "psw-shift-handoff",
        "version": "1.0.0",
        "model_type": "clinical-heuristic",
        "description": "test",
        "card": {
            "id": "psw-shift-handoff", "version": "1.0.0",
            "model_type": "clinical-heuristic", "description": "test",
            "intended_use": "test", "training_data": "test",
            "evaluation_metrics": {}, "ethical_considerations": "",
            "clinical_validation": "", "phipa_compliance": "",
            "license": "Apache-2.0",
        },
        "artifact_sha256": "00" * 32,
        "artifact_size_bytes": 0,
        "created_at": "2026-06-29T00:00:00Z",
    }
    canonical = json.dumps(manifest, sort_keys=True).encode()
    sig = sk.sign(canonical).signature
    manifest["signature"] = {"key_id": "default", "algorithm": "ed25519", "value": sig.hex()}
    (registry_dir / "psw-shift-handoff.v1.0.0.manifest.json").write_text(json.dumps(manifest))

    # Use the registry + audit + consent
    registry = ModelRegistry(registry_path=registry_dir)
    await registry.load_all()
    audit = AuditLogger(audit_path=tmp_paths["audit"])
    consent = ConsentEngine(consent_path=tmp_paths["consent"])

    # Grant consent
    token = await consent.grant_consent("resident-001", ["*"], "psw-brian")

    # Inference
    model = registry.get("psw-shift-handoff")
    await consent.check("resident-001", model.id, consent_token=token)
    out = await model.run({
        "notes": "BP 120/80, walked 10m",
        "observations": {"bp": "120/80", "ambulation": "walked 10m"},
        "resident_id": "r1",
        "psw_id": "psw-brian",
    })
    eid = await audit.log(event_type="inference", patient_id="resident-001", model_id=model.id, model_version=model.version)

    # Verify
    assert "Vitals" in out["shift_handoff"]["summary"]
    events = await audit.query(patient_id="resident-001")
    assert len(events) == 1
    assert events[0]["event_type"] == "inference"
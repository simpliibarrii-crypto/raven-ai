#!/usr/bin/env python3
"""Generate signing key + sample signed model manifest for openclinical-ai.

Usage:
    python tools/sign_manifest.py

Outputs:
    registry/keys/default.pub       — public key (Ed25519)
    registry/psw-shift-handoff.v1.0.0.manifest.json — signed manifest
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from nacl.signing import SigningKey, VerifyKey

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "registry"
KEYS_DIR = REGISTRY / "keys"


def main() -> int:
    KEYS_DIR.mkdir(parents=True, exist_ok=True)

    private_path = KEYS_DIR / "default.key"
    public_path = KEYS_DIR / "default.pub"

    # Generate or load signing key
    if private_path.exists():
        sk = SigningKey(bytes.fromhex(private_path.read_text().strip()))
        print(f"loaded existing signing key: {private_path}")
    else:
        sk = SigningKey.generate()
        private_path.write_text(sk.encode().hex())
        private_path.chmod(0o600)
        print(f"generated new signing key: {private_path}")

    vk = sk.verify_key
    public_path.write_text(bytes(vk).hex())
    public_path.chmod(0o644)
    print(f"wrote public key: {public_path}")

    # Build the manifest (without signature)
    manifest = {
        "id": "psw-shift-handoff",
        "version": "1.0.0",
        "model_type": "clinical-heuristic",
        "description": (
            "PSW shift-handoff documentation assistant. Captures vitals, mobility, "
            "intake/output, mood, incidents, family contact events. Heuristic "
            "categorization + concern detection + summary generation."
        ),
        "card": {
            "id": "psw-shift-handoff",
            "version": "1.0.0",
            "model_type": "clinical-heuristic",
            "description": "PSW shift-handoff documentation assistant (heuristic MVP).",
            "intended_use": (
                "Personal Support Workers (PSWs) in long-term care and retirement "
                "home settings to document end-of-shift handoffs via voice or "
                "structured input. Generates FHIR-compatible structured "
                "observations and a human-readable summary."
            ),
            "training_data": (
                "MVP uses deterministic heuristics (no ML training). Future "
                "versions will be fine-tuned on anonymized PSW shift notes."
            ),
            "evaluation_metrics": {
                "mvp_validation": "manual review by Brian Clerjuste, PSW with 10 years experience",
                "next_milestone": "pilot at Gary J Armstrong Retirement Home",
            },
            "ethical_considerations": (
                "Designed for augmenting — not replacing — PSW judgment. All "
                "outputs require PSW review before being included in the "
                "clinical record. Patient consent is required before any "
                "processing. Audit trail captures every inference."
            ),
            "clinical_validation": (
                "Pre-clinical validation. Real clinical validation requires "
                "pilot deployment with ethics board approval."
            ),
            "phipa_compliance": (
                "PHIPA-aligned: opt-in consent, audit trail, data minimization, "
                "purpose-limited processing."
            ),
            "license": "Apache-2.0",
        },
        "artifact_sha256": "0000000000000000000000000000000000000000000000000000000000000000",
        "artifact_size_bytes": 0,
        "created_at": "2026-06-29T01:35:00Z",
    }

    # Sign: signature is over the canonical JSON (sorted keys) WITHOUT the signature field
    canonical = json.dumps(manifest, sort_keys=True).encode()
    signature = sk.sign(canonical).signature

    manifest["signature"] = {
        "key_id": "default",
        "algorithm": "ed25519",
        "value": signature.hex(),
    }

    manifest_path = REGISTRY / "psw-shift-handoff.v1.0.0.manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2))
    print(f"wrote signed manifest: {manifest_path}")

    # Verify
    verify_key = VerifyKey(bytes.fromhex(public_path.read_text().strip()))
    verify_key.verify(canonical, signature)
    print("signature verified OK")

    return 0


if __name__ == "__main__":
    sys.exit(main())
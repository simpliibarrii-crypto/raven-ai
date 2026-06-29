#!/usr/bin/env python3
"""Grant sample consent records for demo + testing.

Usage:
    python tools/grant_consent.py <patient_id> <psw_id>
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# Make runtime importable when run from anywhere
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from runtime.config import settings
from runtime.consent import ConsentEngine


async def grant(patient_id: str, granted_by: str, scope: list[str] | None = None) -> str:
    engine = ConsentEngine(settings.consent_path)
    scope = scope or ["*"]
    token = await engine.grant_consent(
        patient_id=patient_id,
        scope=scope,
        granted_by=granted_by,
    )
    print(f"consent granted for patient {patient_id} (token: {token})")
    return token


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("usage: grant_consent.py <patient_id> <granted_by>")
        sys.exit(1)
    patient_id = sys.argv[1]
    granted_by = sys.argv[2]
    asyncio.run(grant(patient_id, granted_by))
#!/bin/bash
# Run the openclinical-ai runtime locally for development.
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
export PYTHONPATH="${SCRIPT_DIR}${PYTHONPATH:+:$PYTHONPATH}"
export OPENCLINICAL_REGISTRY_PATH="${OPENCLINICAL_REGISTRY_PATH:-${SCRIPT_DIR}/registry}"
export OPENCLINICAL_AUDIT_PATH="${OPENCLINICAL_AUDIT_PATH:-${SCRIPT_DIR}/.runtime/audit}"
export OPENCLINICAL_CONSENT_PATH="${OPENCLINICAL_CONSENT_PATH:-${SCRIPT_DIR}/consent}"
export OPENCLINICAL_TENANTS_PATH="${OPENCLINICAL_TENANTS_PATH:-${SCRIPT_DIR}/tenants}"
mkdir -p "$OPENCLINICAL_AUDIT_PATH" "$OPENCLINICAL_TENANTS_PATH"
exec python3 -m uvicorn runtime.server:app --host 127.0.0.1 --port 8088 --log-level info "$@"
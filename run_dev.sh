#!/bin/bash
# Run the openclinical-ai runtime locally for development.
set -e
export PYTHONPATH="/workspace/openclinical-ai-scaffold${PYTHONPATH:+:$PYTHONPATH}"
export OPENCLINICAL_REGISTRY_PATH="/workspace/openclinical-ai-scaffold/registry"
export OPENCLINICAL_AUDIT_PATH="/workspace/openclinical-ai-scaffold/.runtime/audit"
export OPENCLINICAL_CONSENT_PATH="/workspace/openclinical-ai-scaffold/consent"
export OPENCLINICAL_TENANTS_PATH="/workspace/openclinical-ai-scaffold/tenants"
mkdir -p "$OPENCLINICAL_AUDIT_PATH" "$OPENCLINICAL_TENANTS_PATH"
exec python3 -m uvicorn runtime.server:app --host 127.0.0.1 --port 8088 --log-level info "$@"
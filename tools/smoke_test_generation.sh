#!/bin/bash
# Smoke test the generative biology AI endpoints + biosecurity screening.
# Verifies:
# 1. Protein generation (ProteinMPNN adapter) — cleared
# 2. DNA generation — cleared
# 3. Pathogen-like sequence — flagged + blocked
# 4. Synthesis order — submitted with biosecurity hash
set -e

cd /workspace/openclinical-ai-scaffold
pkill -f "uvicorn runtime.server:app" 2>/dev/null || true
sleep 2
rm -rf tenants/ consent/ audit/ biosecurity/ .runtime/

export PYTHONPATH=/workspace/openclinical-ai-scaffold
export OPENCLINICAL_REGISTRY_PATH=/workspace/openclinical-ai-scaffold/registry
export OPENCLINICAL_AUDIT_PATH=/workspace/openclinical-ai-scaffold/.runtime/audit
export OPENCLINICAL_CONSENT_PATH=/workspace/openclinical-ai-scaffold/consent
export OPENCLINICAL_TENANTS_PATH=/workspace/openclinical-ai-scaffold/tenants
mkdir -p "$OPENCLINICAL_AUDIT_PATH" "$OPENCLINICAL_TENANTS_PATH" "$OPENCLINICAL_CONSENT_PATH"

python3 -m uvicorn runtime.server:app --host 127.0.0.1 --port 8088 --log-level warning > /tmp/server.log 2>&1 &
SERVER_PID=$!
sleep 3

echo "=== server pid $SERVER_PID ==="

echo ""
echo "--- signin ---"
SIGNIN=$(curl -s -X POST http://127.0.0.1:8088/v1/auth/signin \
  -H 'Content-Type: application/json' \
  -d '{"tenant_id": "bayshore-ottawa", "psw_id": "psw-brian", "method": "password"}')
TOKEN=$(echo "$SIGNIN" | python3 -c "import sys, json; print(json.load(sys.stdin).get('token',''))")

echo ""
echo "--- /v1/generate/protein (ProteinMPNN stub, should be CLEARED) ---"
PROT_PAYLOAD=$(python3 -c "
import json
print(json.dumps({
  'tenant_id': 'bayshore-ottawa',
  'model_id': 'proteinmpnn-inverse-fold',
  'inputs': {
    'constraints': {'length': 100, 'motif': 'HEL'},
    'model_params': {'temperature': 0.1}
  }
}))")
curl -s -X POST http://127.0.0.1:8088/v1/generate/protein \
  -H 'Content-Type: application/json' \
  -H "X-Tenant-ID: bayshore-ottawa" \
  -H "X-Tenant-API-Key: $TOKEN" \
  -H "X-PSW-ID: psw-brian" \
  -d "$PROT_PAYLOAD"

echo ""
echo ""
echo "--- /v1/generate/dna (clean DNA, should be CLEARED) ---"
DNA_PAYLOAD=$(python3 -c "
import json
print(json.dumps({
  'tenant_id': 'bayshore-ottawa',
  'model_id': 'esm3-multimodal',
  'inputs': {
    'constraints': {'length': 100, 'sequence_type': 'dna'}
  }
}))")
curl -s -X POST http://127.0.0.1:8088/v1/generate/dna \
  -H 'Content-Type: application/json' \
  -H "X-Tenant-ID: bayshore-ottawa" \
  -H "X-Tenant-API-Key: $TOKEN" \
  -H "X-PSW-ID: psw-brian" \
  -d "$DNA_PAYLOAD"

echo ""
echo ""
echo "--- biosecurity screening: direct screener call (toxin-like) ---"
PYTHONPATH=/workspace/openclinical-ai-scaffold python3 -c "
from runtime.bio_security import BiosecurityScreener
s = BiosecurityScreener()

print('--- clean protein (should clear) ---')
r = s.screen('MKTLLLTLVVVTIVCLDLGYTFGSQAR', 'protein')
print(f'cleared={r.cleared} risk={r.risk_score} flags={r.flags}')

print('--- botulinum-like pattern (should flag + block) ---')
r = s.screen('MCNHCVVLCGRRRLYYLKGGRLightChainRHeavyChain', 'protein')
print(f'cleared={r.cleared} risk={r.risk_score} flags={r.flags}')

print('--- SARS-CoV-2 spike motif (should flag) ---')
r = s.screen('MYSFVSEETGTLIVNSVLLFLAFVVFLLVTFGVLTRRBDACE2furincleavage', 'protein')
print(f'cleared={r.cleared} risk={r.risk_score} flags={r.flags}')

print('--- AI-evasion pattern (low-complexity glycine-rich) ---')
r = s.screen('MGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGG', 'protein')
print(f'cleared={r.cleared} risk={r.risk_score} flags={r.flags}')

print('--- clean DNA ---')
r = s.screen('ATGCGTACGTAGCTAGCTAGCATCGATCGATCGATCGATCGATCGATCGATCG', 'dna')
print(f'cleared={r.cleared} risk={r.risk_score} flags={r.flags}')
"

echo ""
echo "--- /v1/synthesis/order (after generation) ---"
ORDER_PAYLOAD=$(python3 -c "
import json
print(json.dumps({
  'tenant_id': 'bayshore-ottawa',
  'generation_id': 'gen-001',
  'vendor': 'twist',
  'sequence': 'ATGCGTACGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCG',
  'sequence_type': 'dna',
  'biosecurity_hash': 'abc123'
}))")
curl -s -X POST http://127.0.0.1:8088/v1/synthesis/order \
  -H 'Content-Type: application/json' \
  -H "X-Tenant-ID: bayshore-ottawa" \
  -H "X-Tenant-API-Key: $TOKEN" \
  -H "X-PSW-ID: psw-brian" \
  -d "$ORDER_PAYLOAD"

echo ""
echo ""
echo "--- /v1/biosecurity/audit ---"
curl -s "http://127.0.0.1:8088/v1/biosecurity/audit?tenant_id=bayshore-ottawa&limit=10" \
  -H "X-Tenant-ID: bayshore-ottawa" \
  -H "X-Tenant-API-Key: $TOKEN" \
  -H "X-PSW-ID: psw-brian"

echo ""
echo ""
echo "--- killing server ---"
kill $SERVER_PID 2>/dev/null || true
wait $SERVER_PID 2>/dev/null || true

echo ""
echo "=== server log tail ==="
tail -30 /tmp/server.log 2>&1
echo ""
echo "=== smoke test complete ==="
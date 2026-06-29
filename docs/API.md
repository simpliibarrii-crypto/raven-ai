# API Documentation

## Overview

The API surface is designed around runtime health, model/tool dispatch, tenant-aware operations, audit/provenance, and domain workflows.

## Common conventions

- JSON request and response bodies.
- Tenant-aware endpoints should require explicit tenant context.
- Security-sensitive operations should fail closed.
- Clinical or biological outputs should include evidence/provenance where applicable.

## Endpoint groups

### Health

```http
GET /health
```

Returns service status and runtime metadata.

### Models and agents

```http
GET /models
POST /v1/inference
```

Lists available model adapters and submits inference requests.

### Consent and governance

```http
POST /v1/consent/grant
POST /v1/consent/revoke
GET /audit/events
```

Clinical and PHI-aware workflows should use explicit consent, policy, and audit records.

### Workflows

```http
POST /v1/workflows/run
GET /v1/workflows/{id}
```

Runs reproducible agent/tool pipelines and returns traceable outputs.

## OpenAPI

When the service is running, generate the OpenAPI schema from the application runtime and commit a versioned snapshot under `docs/openapi.json`.

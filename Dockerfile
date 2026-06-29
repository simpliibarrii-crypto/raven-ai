# openclinical-ai runtime — single-container substrate MVP
# Sovereign inference runtime + PSW voice UI + signed model registry + audit gateway + consent engine

FROM python:3.11-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates curl \
    && rm -rf /var/lib/apt/lists/*

# Python deps
COPY pyproject.toml /app/
RUN pip install --upgrade pip && pip install \
    'fastapi>=0.110' \
    'uvicorn[standard]>=0.27' \
    'pydantic>=2.6' \
    'pynacl>=1.5' \
    'httpx>=0.27'

# Application
COPY runtime/ /app/runtime/
COPY registry/ /app/registry/
COPY psw-assistant/ /app/psw-assistant/
COPY consent/ /app/consent/
COPY tools/ /app/tools/

# Runtime paths
ENV OPENCLINICAL_REGISTRY_PATH=/app/registry \
    OPENCLINICAL_AUDIT_PATH=/var/lib/openclinical/audit \
    OPENCLINICAL_CONSENT_PATH=/var/lib/openclinical/consent \
    OPENCLINICAL_TENANTS_PATH=/var/lib/openclinical/tenants \
    OPENCLINICAL_CORS_ORIGINS=*

RUN mkdir -p /var/lib/openclinical/audit /var/lib/openclinical/consent /var/lib/openclinical/tenants

EXPOSE 8088

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -fsS http://127.0.0.1:8088/health || exit 1

CMD ["uvicorn", "runtime.server:app", "--host", "0.0.0.0", "--port", "8088", "--log-level", "info"]
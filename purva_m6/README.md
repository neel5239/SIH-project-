# PURVA M6 — Platform Core & Clinical Services

This is a VS Code-first implementation of the PURVA M6 platform layer.

## Run locally

1. Install Docker Desktop.
2. Copy `.env.example` to `.env`.
3. Run:

```powershell
docker compose up --build
```

4. Open:
   - Swagger: http://localhost:8000/docs
   - Health: http://localhost:8000/api/v1/health
   - Readiness: http://localhost:8000/api/v1/ready
   - MinIO console: http://localhost:9001

## Development without Docker

Create a virtual environment and install `requirements.txt`, then set `.env`
with localhost addresses and run:

```powershell
python -m uvicorn services.m6_platform.main:app --reload --port 8000
```

## Demo credentials

Kiosk:
`X-Kiosk-Key: purva-demo-kiosk-key`

Demo staff token:
Use `POST /api/v1/auth/demo-token` with role `physician`, `nurse`, or `admin`.

## Scope

M6 owns the platform plumbing: API gateway, contracts, database, Redis session
vault, MinIO object storage, async jobs, shared LLM runtime adapter, triage,
doctor/patient services, metrics, audit and edge/offline infrastructure.

M6 does NOT implement M3/M4 clinical inference or M5 clinical fusion logic.
Those modules consume the contracts and services here.

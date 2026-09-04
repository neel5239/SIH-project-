# BACKEND / PLATFORM CORE

**Owner:** Member 6 (M6)
**Stack:** Python 3.11 · FastAPI · Pydantic v2 · PostgreSQL · Redis · MinIO · Celery
**Deep spec:** [`docs/06-M6-platform-core.md`](../docs/06-M6-platform-core.md)
**API list:** [`docs/API_SPEC.md`](../docs/API_SPEC.md)

---

## Your responsibility

Five people are building five things that must fit together, fast, without blocking each other.
M6 makes that possible.

**M6 ships first.** On day 1, before anyone else can meaningfully start, deliver:
contracts, database schema, docker-compose, and **mock endpoints for every route**.
Everyone else codes against mocks and swaps in real implementations as they land.

You also own the three surfaces clinicians actually touch — the triage service, the doctor
service, and the metrics service.

**You do not write clinical logic.** M3 and M5 do that. You give them a runtime.

---

## Layout

```
backend/
├── main.py                  FastAPI app + lifespan (loads models, opens pools)
├── api/routes/              one file per surface — see the owner column below
├── api/middleware/          auth · request_id · errors · ratelimit
├── core/
│   ├── config.py            settings from env
│   ├── orchestrator.py      session state machine, module call order
│   ├── llm_runtime.py       ONE shared model server — M3 and M5 both use it
│   ├── storage.py           MinIO: audio, images, crops, TTS cache
│   ├── vault.py             Redis session vault, TTL, encryption
│   ├── queue.py             job envelope, retry, dead-letter
│   ├── audit.py             append-only audit writer
│   ├── metrics.py           latency histograms, counters
│   ├── offline.py           connectivity monitor, store-and-forward
│   └── mocks.py             PURVA_MOCK fixture responses
├── db/                      see db/DATABASE_CONTEXT.md
└── workers/                 ocr · fhir outbox · tts prewarm · metrics rollup
```

### Route ownership

| File | Owner | Surface |
|---|---|---|
| `health.py` | M6 | `/health` `/ready` `/health/deps` |
| `session.py` `consent.py` `fhir.py` | M1 | identity, consent, FHIR push |
| `language.py` | M2 | STT / NMT / TTS |
| `conversation.py` | M3 | the interview turn loop |
| `document.py` | M4 | upload, QC, verify queue, crops |
| `summary.py` | M5 | summarise, provenance replay, field edit |
| `doctor.py` `triage.py` `patient.py` `admin.py` | M6 | clinician + ops surfaces |

M1–M5 write the route bodies for their own files. M6 owns the router wiring, middleware,
error envelope, and everything under `core/`.

---

## Two paths, two budgets

| Path | What | Budget |
|---|---|---|
| **Sync** | session, consent, conversation turn, STT/TTS, summary render | **3 s per turn** |
| **Async** | OCR jobs, FHIR push, TTS prewarm, metrics rollup | 60 s per job |

Never block the kiosk on an async job. The patient uploads a document and continues; the
doctor console refreshes live as entities land.

---

## Non-negotiables

1. **`/ready` returns 200 only when every model is resident.** A kiosk that accepts a patient
   before ASR is loaded will hang on question one, on stage.
2. **One LLM runtime.** M3 and M5 send different grammars to the same server. Agree the model
   in week 1 — two runtimes will not fit on the edge node's RAM.
3. **Pre-cut audio segments server-side.** Provenance replay must start in under 300 ms.
4. **Never log PII.** Put a redaction filter in the logger on day 1.
5. **Append-only means append-only.** Revoke UPDATE and DELETE on `audit_log` and
   `guardian_log` at the database level, not by convention.
6. **Instrument latency per stage from the first commit.** You cannot retrofit it with two days left.

---

## Deliverables

**Phase 0 (day 1, blocking):** repo skeleton · `contracts/` · migrations 001–005 ·
docker-compose · every route stubbed with fixtures · `PURVA_MOCK` flags · README run instructions.

**Phase 1:** real DB wiring · async queue · MinIO helpers · LLM container · auth.

**Phase 2:** triage service + WebSocket board · doctor service · **provenance replay endpoint** ·
patient dashboard · audit everywhere.

**Phase 3:** metrics endpoints + admin dashboard · edge compose with model preload ·
offline detect + outbox drain · chaos drills · load test.

---

## Run

```bash
cp .env.example .env
docker compose up --build
PURVA_MOCK=m1,m2,m3,m4,m5 docker compose up      # everything mocked
```

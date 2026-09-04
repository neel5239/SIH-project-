# M6 — Platform Core & Clinical Services

> **Owner:** Member 6
> **Read `00-INTRODUCTION.md` first.**
> **Service path:** `services/m6_platform/` + `contracts/` + `infra/`
> **Branch:** `m6-platform`

---

## 1. Why this module exists

Five people are building five things that must fit together perfectly, in a short time, without blocking each other.

M6 is the module that makes that possible.

**M6 has a special property: it must ship first.** On day 1, before anyone else can meaningfully start, M6 delivers the repository skeleton, the shared data contracts, the database schema, and **mock endpoints for every API in the system**. Everyone else then codes against mocks and swaps in real implementations as they land.

**If M6 is late, the whole project is late.** If M6 ships day 1, nobody is ever blocked.

M6 also owns three things the doctors and nurses actually touch: the **triage service** (which makes USP #3 real), the **doctor service** (which makes USP #1 real), and the **metrics service** (which makes USP #2 and #9 visible).

---

## 2. Responsibilities

| # | Responsibility | Detail |
|---|---|---|
| 1 | **Shared contracts** | Pydantic models every module imports — the single source of truth |
| 2 | **API gateway** | FastAPI app, routing, auth, rate limiting, error envelope |
| 3 | **Database** | Postgres schema, migrations, connection pooling |
| 4 | **Session vault** | Redis with TTL, encrypted values |
| 5 | **Object storage** | MinIO for audio blobs, document images, crops, TTS cache |
| 6 | **Async job queue** | Celery/RQ for OCR jobs and FHIR pushes |
| 7 | **LLM runtime** | One shared model server for M3 and M5 |
| 8 | **Triage service** | Red-flag queue, re-sequencing, nurse notification |
| 9 | **Doctor service** | Summary fetch, edit, sign, provenance replay |
| 10 | **Patient service** | Personal dashboard data, timeline, consent revocation |
| 11 | **Metrics service** | Guardian counter, field accuracy, latency per stage |
| 12 | **Edge deployment** | Docker compose, model preloading, offline sync worker |
| 13 | **Observability** | Structured logs, health checks, latency histograms |
| 14 | **Mock server** | Day-1 deliverable — fixture responses for every endpoint |

### Explicitly NOT this module's job

- Any clinical logic (M3, M5)
- Any model inference logic (M2, M4)
- Frontend (separate work-stream)

---

## 3. Architecture

```
                            CLIENTS
        kiosk PWA · doctor console · triage board · patient app
                               │
                               ▼
                    API GATEWAY  (FastAPI)
                    routing · auth
                    validation · rate limit
                    error envelope · request id
                               │
                   ┌───────────┴───────────┐
                   ▼                       ▼
              SYNC PATH               ASYNC PATH
           LOW LATENCY               THROUGHPUT
           budget 3 s / turn         budget 60 s / job
                   │                       │
                   ▼                       ▼
           session create            OCR jobs        (M4)
           consent                   FHIR push       (M1)
           conversation turns  (M3)  TTS pre-warm    (M2)
           language STT/TTS    (M2)  offline sync
           summary render      (M5)  metrics rollup
                   │                       │
                   │              Celery / RQ workers
                   │              retry · backoff
                   │              dead-letter → admin
                   │                       │
                   └───────────┬───────────┘
                               ▼
                          DATA LAYER
                               │
          ┌────────────────────┼────────────────────┐
          ▼                    ▼                    ▼
     PostgreSQL 16          Redis                MinIO
     patients            session vault        audio blobs
     sessions            (TTL, encrypted)     document images
     consents            job queue            crops
     slots               pipeline config      TTS cache
     documents           cache                consent audio
     doc_entities
     summaries
     provenance
     alerts
     corrections
     guardian_log   (append-only)
     audit_log      (append-only)
     fhir_outbox
     triage_queue
                               │
      ┌─────────────┬──────────┼──────────┬─────────────┐
      ▼             ▼          ▼          ▼             ▼
   TRIAGE       DOCTOR      METRICS    PATIENT       ADMIN
   SERVICE      SERVICE     SERVICE    SERVICE       SERVICE
      │             │          │          │             │
      ▼             ▼          ▼          ▼             ▼
 red-flag Q    summary     Guardian   own timeline  offline state
 re-sequence   fetch       counter    lab trends    dead letters
 nurse push    field edit  field      audio recap   engine mix
 verify queue  sign        accuracy   consent       disk / health
 WebSocket     PROVENANCE  latency    revoke
 live push     REPLAY      p50 / p95
               (tap a line
                → hear the
                patient)
                               │
                               ▼
                        LLM RUNTIME  (shared)
                        one model server
                        two grammars
                        M3 slot schema
                        M5 summary schema
                        llama.cpp / vLLM · 4-bit
                               │
                               ▼
                           EDGE NODE
                    docker compose
                    models preloaded at boot
                    /ready gate
                               │
                    connectivity monitor
                               │
                   ┌───────────┴───────────┐
                   ▼                       ▼
                ONLINE                  OFFLINE
                   │                       │
                   ▼                       ▼
            normal operation         M2 → local models
            outbox drains            M1 → queue FHIR
                   │                 everything else
                   │                 unaffected
                   │                       │
                   └───────────┬───────────┘
                               ▼
                        on reconnect
                     outbox drains, sync logged
                     serves 4–8 kiosks
```

---

## 4. Component detail

### 4.1 Shared contracts — the day-1 deliverable

`contracts/` is imported by every module. It is the **single source of truth** for every object that crosses a module boundary.

```python
# contracts/slot.py
from pydantic import BaseModel, Field
from typing import Literal, Any
from uuid import UUID
from datetime import datetime

class SlotSource(BaseModel):
    type: Literal["audio", "touch", "inferred"]
    audio_blob_id: UUID | None = None
    audio_offset_ms: tuple[int, int] | None = None
    raw_transcript: str | None = None
    translated: str | None = None

class Slot(BaseModel):
    slot_id: UUID
    session_id: UUID
    ontology_key: str
    value: Any
    value_type: Literal["string", "number", "boolean", "enum", "enum_multi", "scale"]
    unit: str | None = None
    confidence: float = Field(ge=0, le=1)
    framework: Literal["socrates", "ros", "dashavidha", "demographics", "general"]
    section: str
    answered_by: Literal["self", "proxy"] = "self"
    input_mode: Literal["voice", "touch"]
    provenance_id: UUID | None = None
    created_at: datetime
```

Same treatment for `Session`, `DocEntity`, `Alert`, `ClinicalSummary`, `Provenance`, `Consent`.

**Contract change protocol:**
1. Propose in the group channel with the reason
2. Bump `CONTRACT_VERSION`
3. Update this doc and `00-INTRODUCTION.md` §9
4. Update the mock fixtures
5. Announce; affected owners confirm

**Contract drift is the number one way a 6-person hackathon project dies.** Enforce this.

### 4.2 The mock server — the most important thing M6 ships

Every endpoint in `00-INTRODUCTION.md` §9.7 returns realistic fixture data from day 1.

```python
# services/m6_platform/mocks.py
MOCK_MODE = os.getenv("PURVA_MOCK", "").split(",")   # e.g. "m3,m4,m5"

@router.post("/session/{sid}/turn")
async def turn(sid: UUID, body: TurnRequest):
    if "m3" in MOCK_MODE:
        return fixtures.next_question(sid)          # canned, but valid shape
    return await m3_client.turn(sid, body)
```

**Per-module mock flags.** M2 can develop with `PURVA_MOCK=m1,m3,m4,m5` and get a fully working system around them. As each module lands, its flag is removed.

**Fixtures must be realistic and clinically plausible.** Three scenario sets:
- `fixtures/normal_fever.json`
- `fixtures/cardiac_redflag.json`
- `fixtures/ayush_return_visit.json`

These double as the demo scenarios and the integration test data. Build them once, use them everywhere.

### 4.3 API conventions

Everyone follows these. Set them on day 1 and do not renegotiate.

```
Base path:     /api/v1
Auth:          kiosk → X-Kiosk-Key header
               staff → Bearer JWT (role: physician | nurse | admin)
               patient → Bearer JWT (scoped to own ABHA)
Request id:    X-Request-ID, generated if absent, echoed, logged
Idempotency:   Idempotency-Key on all POSTs that create resources
Error shape:
  {
    "error": {
      "code": "CONSENT_REQUIRED",
      "message": "Session has no valid consent artefact.",
      "request_id": "...",
      "retryable": false
    }
  }
Async jobs:
  POST returns 202 { job_id, status: "queued", poll_url }
  GET  poll_url  → { status, result | error }
Pagination:    ?limit=50&cursor=...
Timestamps:    ISO 8601 with timezone, always
```

**Never put PII in a URL or query string.** Session IDs are opaque UUIDs. ABHA IDs go in request bodies over TLS only.

### 4.4 Triage service (makes USP #3 real)

When M3 fires a red flag, this service turns it into an actual change in the physical queue.

```
        M3 fires Alert(red_flag, critical)
                        │
                        ▼
              1  WRITE TO triage_queue
                 priority = 0
                        │
                        ▼
              2  RE-SEQUENCE TOKENS
                 this patient → front
                 others shift +1
                        │
                        ▼
              3  PUSH TO TRIAGE BOARD
                 WebSocket / SSE
                 nurse sees it now, no refresh
                        │
                        ▼
              4  NOTIFY PHYSICIAN ON DUTY
                        │
                        ▼
              5  EMIT AUDIT EVENT
```

**Use WebSocket or Server-Sent Events for the triage board.** Polling every 5 seconds looks and feels wrong for an emergency surface. The board must update *while the judges are watching*, with no refresh.

**Triage board also shows:**
- The verify queue from M4 (unreadable ink awaiting a human)
- Sessions in progress with elapsed time
- Sessions abandoned mid-way

```sql
CREATE TABLE triage_queue (
    entry_id        UUID PRIMARY KEY,
    session_id      UUID NOT NULL,
    token_number    INT NOT NULL,
    priority        INT NOT NULL DEFAULT 100,  -- 0 = red flag, front
    reason          TEXT,
    rule_id         TEXT,
    status          TEXT NOT NULL,   -- waiting | called | seen | left
    entered_at      TIMESTAMPTZ DEFAULT now(),
    acknowledged_by TEXT,
    acknowledged_at TIMESTAMPTZ
);
```

### 4.5 Doctor service (makes USP #1 real)

```
GET  /api/v1/doctor/queue
     → patients ready, with red-flag markers, sorted by priority then token

GET  /api/v1/doctor/session/{id}/summary
     → ClinicalSummary (from M5) + alerts + timeline + delta

GET  /api/v1/doctor/provenance/{prov_id}
     → audio stream at the exact offsets, OR the image crop
     → WRITES AN AUDIT EVENT (provenance_replayed)

PATCH /api/v1/doctor/summary/{id}/field
     → apply edit, store correction, update accuracy metrics

POST /api/v1/doctor/summary/{id}/sign
     → mark signed, trigger M1's FHIR push
```

**The provenance replay endpoint is the highest-value endpoint in the project.** Get it fast and reliable.

```python
@router.get("/doctor/provenance/{prov_id}")
async def replay(prov_id: UUID, user=Depends(require_physician)):
    prov = await db.get_provenance(prov_id)
    await audit.log("provenance_replayed", actor=user.id, resource=prov_id)

    if prov.kind == "audio_offset":
        if not consent_allows_audio(prov.session_id):
            return {"kind": "transcript_only",
                    "transcript_local": prov.transcript_local,
                    "transcript_english": prov.transcript_english}
        return {"kind": "audio",
                "url": signed_url(prov.audio_blob, prov.start_ms, prov.end_ms),
                "transcript_local": prov.transcript_local}

    return {"kind": "image",
            "url": signed_url(prov.crop_blob),
            "page": prov.page, "bbox": prov.bbox}
```

**Serve a pre-cut audio segment**, not the whole recording with a client-side seek. Cut it server-side with ffmpeg, cache the segment. Playback must start in under 300 ms or the magic dies.

### 4.6 Metrics service (makes USP #2 and #9 visible)

```
GET /api/v1/metrics/guardian
    { outputs_checked, blocked_diagnostic, blocked_therapeutic,
      emitted_diagnostic: 0, version }

GET /api/v1/metrics/accuracy?window=7d
    { by_section: { drugs: 0.91, hpi: 0.87, ... },
      by_source_module: { M3: 0.89, M4: 0.79 },
      trend: [ { date, accuracy } ] }

GET /api/v1/metrics/latency
    { turn_p50_ms, turn_p95_ms,
      by_stage: { stt, nmt, dialogue, tts },
      engine_mix: { bhashini: 0.87, local: 0.13 } }

GET /api/v1/metrics/throughput
    { sessions_today, avg_duration_s, completion_rate,
      abandonment_rate, red_flags_fired }
```

**These four endpoints are demo assets.** Build a simple admin dashboard that renders them. Minute 7:15 of the demo is the Guardian counter.

**Instrument latency per stage from day 1.** When the kiosk feels slow in week 3, you need to know *which* stage is slow. Retrofitting instrumentation under time pressure is miserable.

### 4.7 Async job queue

```
Sync (must be fast — patient is waiting):
  session create, consent, conversation turn, STT, TTS, summary render

Async (can take seconds):
  OCR pipeline           (M4) — 3-15 s
  FHIR bundle + push     (M1) — 1-5 s, may fail and retry
  TTS pre-warm           (M2) — speculative
  Offline outbox drain   (M1) — background
  Metrics rollup         (M6) — periodic
```

**Never block the kiosk on an async job.** The patient uploads a document and continues. If they finish before OCR does, the summary is generated with whatever entities are ready and updated when the rest land — the doctor's console refreshes live.

```
Job envelope:
  { job_id, type, session_id, payload, status,
    attempts, max_attempts, last_error,
    created_at, started_at, finished_at }

Retry: exponential backoff, 5 attempts, dead-letter after that
Dead letter → admin dashboard, never silently lost
```

### 4.8 LLM runtime — shared, not duplicated

M3 needs constrained slot filling. M5 needs constrained summary generation. **One model server, two grammars.**

```
llama.cpp server (or vLLM) on the edge node
  · one 4-bit quantised instruct model
  · loaded once at boot
  · GBNF grammar passed per request
  · M3 sends its slot schema
  · M5 sends its summary schema
```

**Coordinate this explicitly between M3, M5 and M6.** Two separate runtimes will not fit in the edge node's RAM alongside the ASR, TTS and OCR models. Agree the model and the serving stack in week 1.

### 4.9 Storage layout (MinIO)

```
purva-audio/
  {session_id}/
    turn-{n}.wav              # full turn recordings
    consent-assent.wav
    segments/{prov_id}.wav    # pre-cut provenance segments (cached)

purva-documents/
  {session_id}/
    {document_id}/
      original.jpg            # NEVER delete before retention expiry
      processed.jpg
      crops/{entity_id}.jpg   # for "show me the ink"

purva-tts-cache/
  {lang}/{hash}.wav

purva-consent-audio/
  {version}/{lang}.wav        # pre-generated, long-lived
```

**Retention:** driven by M1's consent artefact. Default — delete audio and document originals at session end unless `retain_audio` / `retain_documents` were granted. The purge job is M1's logic, M6's infrastructure.

### 4.10 Edge deployment & offline

```yaml
# infra/edge/docker-compose.yml (shape)
services:
  gateway:      # FastAPI, all modules
  postgres:
  redis:
  minio:
  llm:          # llama.cpp server, model preloaded
  asr:          # local IndicConformer
  tts:          # local Indic-TTS
  ocr:          # PaddleOCR + TrOCR
  worker:       # Celery
  sync:         # offline outbox drain
```

**Boot sequence matters.** Preload every model at container start and expose a `/ready` endpoint that only returns 200 when all models are resident. A kiosk that accepts a patient before the ASR model is loaded will hang on the first question.

**Offline detection:**

```
connectivity monitor (checks every 15 s)
    │
  online ──► normal operation, outbox drains
    │
  offline ─► · M2 switches to local models (transparent)
             · M1 queues FHIR bundles in outbox
             · everything else unaffected
             · admin dashboard shows OFFLINE state
    │
  reconnect ─► outbox drains automatically, log the sync
```

**Demo:** pull the cable. Complete a session. Plug it back in. Watch the outbox drain. This is USP #8 and M6 owns the plumbing.

### 4.11 Observability

```
Structured JSON logs, every line:
  { ts, level, request_id, session_id, module, event, duration_ms, ... }

Health:
  GET /health         → { status, version }
  GET /ready          → 200 only when all models loaded and DB reachable
  GET /health/deps    → per-dependency status (postgres, redis, minio,
                        bhashini, llm, abdm)

Counters to expose:
  turn_latency_ms (histogram, by stage)
  ocr_job_duration_ms
  guardian_blocks_total (by label)
  red_flags_fired_total (by rule_id)
  fhir_push_total (by status)
  engine_used_total (bhashini | local)
  sessions_total (by end_reason)
```

---

## 5. Database — full schema ownership

M6 owns the migration chain. Other modules propose tables; M6 writes and versions the migrations.

```
alembic/versions/
  001_core.py          sessions, patients, consents, audit_log
  002_conversation.py  slots, interview_state, red_flag_events
  003_documents.py     documents, doc_entities, ocr_training_pairs
  004_summary.py       summaries, provenance, corrections,
                       guardian_log, prakriti_scores
  005_platform.py      triage_queue, jobs, fhir_outbox, metrics_rollup
```

**Rules:**
- `audit_log` and `guardian_log` are append-only — revoke UPDATE/DELETE at the DB level
- Every table with patient data has `session_id` indexed
- `name` and `phone` are encrypted at the column level
- Every migration is reversible or explicitly marked irreversible

---

## 6. Security baseline

| Area | Requirement |
|---|---|
| Transport | TLS everywhere, including kiosk → gateway on the local network |
| At rest | Postgres encrypted volume; MinIO server-side encryption; Redis values encrypted before write |
| Column-level | `patients.name_enc`, `patients.phone_enc` |
| Auth | Kiosk API key per device; staff JWT with role claims; patient JWT scoped to own ABHA |
| Authorisation | Physician can read any queued patient; patient can read only their own; nurse sees triage only |
| Audit | Every access to clinical data logged, including provenance replay |
| Secrets | Environment variables, never committed. `.env.example` in repo, `.env` gitignored |
| PII in logs | **Never.** Log session IDs, not names. Redact at the logger. |
| Rate limiting | Per kiosk key and per staff token |

---

## 7. Dependencies

| Depends on | For what |
|---|---|
| Nothing | **M6 is the base layer. It ships first.** |

| Provides to | What |
|---|---|
| **Everyone** | Contracts, database, storage, queue, gateway, mock server, LLM runtime, observability |
| **M1** | Outbox worker, audit infrastructure, Redis vault |
| **M2** | MinIO for audio and TTS cache, Redis for pipeline config |
| **M3** | LLM runtime, slot storage |
| **M4** | Async job queue, MinIO for images and crops |
| **M5** | LLM runtime, provenance storage, metrics endpoints |
| **Frontend** | Every API surface |

---

## 8. Failure modes

| Failure | Required behaviour |
|---|---|
| Postgres down | Gateway returns 503 with a clear error. Kiosk shows "please see the registration desk". No silent data loss. |
| Redis down | Session vault unavailable → sessions cannot start. Fail fast and loudly, do not half-work. |
| MinIO down | Audio/documents cannot be stored. Conversation can continue with provenance degraded to transcript-only. Document upload fails with a clear message. |
| LLM runtime down | M3 falls back to closed-question-only mode. M5 falls back to the template renderer. **The kiosk keeps working.** |
| A worker crashes mid-job | Job returns to queue, retried. Idempotency keys prevent duplicate side-effects. |
| Dead-letter queue growing | Surface on the admin dashboard. Never silently discard. |
| Disk full on edge node | Alert at 80%. Refuse new document uploads at 95% rather than corrupting. |
| Clock skew | Use server time for all timestamps. Never trust a kiosk clock. |

---

## 9. Testing

**Contract tests — M6 owns these, they protect everyone**
- Every module's output validates against the shared Pydantic model
- Run in CI on every push. A contract violation fails the build.

**Integration**
- Full happy path with all modules mocked, then progressively unmocked
- The three fixture scenarios run end to end
- Async job lifecycle: submit → process → poll → result
- Retry and dead-letter behaviour under injected failures

**Load (do a light version — it makes a good pitch line)**
- 8 concurrent kiosk sessions on one edge node
- Measure turn latency p95 under load
- Confirm the node does not thrash when OCR and conversation run together

**Chaos drills — run these before the demo**
- Kill Bhashini connectivity mid-session
- Kill the LLM runtime mid-summary
- Kill Postgres and restart
- Fill the disk
- Pull the network cable mid-FHIR-push

**Each drill must end with the kiosk still usable and no data lost.** Practise the network-cable one specifically, because it is in the demo script.

---

## 10. Build order

**Phase 0 — DAY 1, BLOCKING FOR EVERYONE**
- [ ] Repo skeleton, branch strategy, `.env.example`
- [ ] `contracts/` — all six Pydantic models
- [ ] `docker-compose.yml` — postgres, redis, minio, gateway
- [ ] Alembic migration 001 + 002 + 003 + 004 + 005 (schema for everything)
- [ ] FastAPI app with **every endpoint from §9.7 stubbed and returning fixtures**
- [ ] Three fixture scenario files
- [ ] `PURVA_MOCK` per-module flag mechanism
- [ ] README: how to run the whole thing in one command

**Announce completion in the group. Everyone starts.**

**Phase 1**
- [ ] Real database wiring, replacing fixture reads
- [ ] Async queue with Celery/RQ
- [ ] MinIO storage helpers
- [ ] LLM runtime container, shared
- [ ] Auth (kiosk key + staff JWT)

**Phase 2**
- [ ] Triage service + WebSocket board updates
- [ ] Doctor service: queue, summary fetch, edit, sign
- [ ] **Provenance replay endpoint with server-side audio cutting**
- [ ] Patient dashboard endpoints
- [ ] Audit logging wired everywhere

**Phase 3**
- [ ] Metrics service, all four endpoints
- [ ] Admin dashboard rendering them
- [ ] Edge compose with model preloading + `/ready`
- [ ] Offline detection + outbox drain worker
- [ ] Chaos drills
- [ ] Load test

---

## 11. Demo checklist — what M6 must show

1. **The triage board updating live** when M3 fires the red flag. No refresh. WebSocket push. Token re-sequencing visible on screen.
2. **Provenance replay** — the doctor taps, audio starts in under 300 ms. If it lags, the magic dies. This is M6's latency problem to solve.
3. **Pull the network cable.** Show the admin dashboard flipping to OFFLINE, the session continuing, the outbox filling, and then draining on reconnect.
4. **The metrics dashboard** — Guardian counter, latency by stage, engine mix (Bhashini vs local). Minute 7:15.
5. **`docker compose up` on one machine.** Say: *"This entire platform runs on one ₹40,000 box inside the hospital. Patient audio never leaves the building."*

---

## 12. Notes and gotchas

- **Ship Phase 0 on day 1. Nothing else you do matters as much.** Five people idle for a day is a fifth of a hackathon gone.
- **Mock fixtures must be clinically realistic**, not `"foo": "bar"`. They become the demo scenarios and the test data. Write them properly once.
- **Instrument latency from the first commit.** You cannot retrofit it when the kiosk feels slow with two days left.
- **One LLM runtime.** Agree this with M3 and M5 in week 1 or you will discover the RAM problem on demo day.
- **Server-cut audio segments.** Streaming the whole recording and seeking client-side will feel sluggish and will occasionally play the wrong thing.
- **Append-only means append-only.** Revoke UPDATE and DELETE on `audit_log` and `guardian_log` at the database level, not by convention.
- **Never log PII.** Put a redaction filter in the logger on day 1, not after someone screenshots a log with a patient name in it.
- **The `/ready` endpoint is not optional.** A kiosk that accepts a patient before models are loaded will hang on question one, on stage.
- **Practise the chaos drills before demo day.** The network-cable demo is scripted — rehearse it until it is boring.

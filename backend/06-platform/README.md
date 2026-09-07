# MODULE 06 — PLATFORM

**Path:** `backend/06-platform/`
**Team:** all 6 members contribute. Assign a lead per sprint in standup.
**Everything this module needs lives in this folder.** No shared `api/`, `core/` or
`contracts/` folder — if this module needs it, it is here.

---

## What this module is for

Database, storage, background jobs, configuration, and the FastAPI application that mounts
every other module's router.

**It carries no clinical logic of its own.** It is what the other five modules run on.
**It ships first**, because the schema and the mock endpoints unblock everyone else.

---

## 🔌 CONNECTIONS — who calls this, and what it calls next

```
   01-AUTH   02-QUESTIONNAIRE   03-OCR   04-SUMMARY   05-DOCTOR
      │            │              │          │            │
      └────────────┴──────┬───────┴──────────┴────────────┘
                          ▼
              ┌────────────────────────────┐
              │       06-PLATFORM          │  ◄── you are here
              │                            │
              │  app.py  mounts every      │
              │          module's router   │
              │  database/  storage/       │
              │  jobs/  config/  runtime/  │
              │  http/middleware · ws      │
              └────────────────────────────┘

        every module stands on this — nothing stands on them
```

### Called by

**All five other modules**, on every request. It is imported, not called in sequence.

```python
from platform_runtime import storage, cache, logging, deps
```

### Calls next

**Nothing in the clinical pipeline.** It has no place in the patient → doctor sequence.

It does two things *for* the others:

| | |
|---|---|
| `app.py` | discovers and mounts each module's `api.py` router at startup |
| `jobs_runtime/` | runs background work **on behalf of** modules 03 and 04 |

### What it hands over

```json
{
  "note": "This module hands over nothing clinical.",
  "provides": [
    "database session + migrations",
    "object storage (S3 / MinIO / local disk)",
    "Redis cache + Celery queue",
    "WebSocket hub for live push to 05",
    "structured logging with PII redaction",
    "settings validated at boot",
    "MOCK fixture responses so nobody is blocked"
  ]
}
```

> **Ship the schema and the mock endpoints on day 1.** Five other modules can then be built in
> parallel against fixtures. If this is late, everything is late.
>
> ```bash
> MOCK=02,03,04 docker compose up
> ```

---

## What is inside this folder

```
06-platform/
├── README.md
├── app.py                 ★ the FastAPI application — mounts every module's router
├── api.py                 /health · /ready · /health/deps
├── schemas.py             the error envelope + shared enums every module imports
├── service.py             startup / shutdown lifecycle
├── config.py              global settings, validated at boot
│
├── database/              schema · repositories · migrations · seed data
│   └── migrations/
├── storage/               audio · documents · originals · crops · retention
├── jobs/                  background job definitions
├── jobs_runtime/          the Celery application
├── config/                provider selection, feature flags
├── runtime/               storage · cache · queue · realtime · security
│                          logging (PII redaction) · audit · deps
├── http/
│   ├── middleware/            auth · request_id · errors · ratelimit
│   ├── ws/                    hub · doctor channel
│   └── mocks.py               fixture responses for MOCK mode
└── tests/                 contract tests and the full end-to-end path
```

**Every sub-folder has its own README.md.** Open the one you are working in.

| File | Does |
|---|---|
| `api.py` | this module's FastAPI router — mounted by `06-platform/app.py` |
| `schemas.py` | **what this module exposes to other modules** — the only thing they may import |
| `models.py` | this module's own database tables |
| `service.py` | orchestration — ties the sub-parts together |
| `config.py` | this module's settings, read from env |

---

## Import rules

```
✅  from platform_runtime import storage, cache, logging     # shared runtime is fine
✅  import 06-platform.schemas                                  # another module's PUBLIC schemas
❌  import 06-platform.service                                  # another module's internals
❌  import 06-platform.models                                   # another module's tables
```

**A module may import another module's `schemas.py` and nothing else.** That file is the
contract. Everything else in this folder is private.

---

## Six rules every module obeys

1. **Never diagnose.** No disease name, no treatment, no drug recommendation — anywhere.
2. **Never state a fact without saying where it came from.**
3. **Never merge conflicting information.** Show both; the doctor decides.
4. **Never block the patient.** Any question is skippable; a partial record is still valuable.
5. **Degrade, never crash.** The patient must never see a stack trace.
6. **The doctor makes the clinical decision.** We collect, structure and present.

> ### The thing to remember
>
> **No clinical logic lives here.** If it knows what a symptom is, it belongs in a module.
>
> And: **a PII redaction filter in the logger from day 1.** No name, phone, OTP or clinical text
> in a log line — ever.

---

## Reference

- `backend/README.md` — how the six modules fit together
- `docs/ARCHITECTURE.md` — the full picture
- the `README.md` inside each sub-folder of this module

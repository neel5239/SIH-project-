# core/ - the runtime everything stands on

**Path:** `backend/06-platform/runtime/`

Shared infrastructure. **No clinical logic lives here.** If it knows what a symptom is, it
belongs in a module.

| File | Does |
|---|---|
| `config.py` | settings from env, **validated at boot** - a missing key fails startup, loudly |
| `security.py` | encryption helpers, password hashing, key handling |
| `storage.py` | object storage adapter - S3 / MinIO / local disk, swappable by config |
| `cache.py` | Redis connection |
| `queue.py` | Celery app, job envelope, retry, dead-letter |
| `realtime.py` | WebSocket hub - push to the doctor portal |
| `audit.py` | append-only audit writer |
| `logging.py` | structured logs + **PII redaction filter** |
| `errors.py` | exception to error-envelope mapping |
| `deps.py` | shared FastAPI dependencies |

## Import direction - one way only

```
core/     ---->  contracts/             (only)
modules/  ---->  contracts/  core/
api/      ---->  modules/  contracts/  core/
workers/  ---->  modules/  core/
```

**`core/` never imports a module. A module never imports another module.**

## Non-negotiables

- [ ] **PII redaction filter in the logger from day 1.** No name, phone, OTP or clinical text
      in a log line - ever.
- [ ] A missing required environment variable fails **startup**, not the first request
- [ ] `/ready` returns 200 only when the database is reachable **and** every model is loaded
- [ ] Swapping a storage backend, an SMS provider or an OCR engine is a **config** change

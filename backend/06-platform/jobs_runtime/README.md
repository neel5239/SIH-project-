# workers/ - background jobs

**Path:** `backend/06-platform/jobs_runtime/`

OCR takes seconds. The patient must never wait for it, and the doctor's screen must fill in as
results land.

| File | Runs | For |
|---|---|---|
| `celery_app.py` | - | the Celery application and queue config |
| `ocr_worker.py` | document processing | module 03 |
| `summary_worker.py` | summary generation | module 04 |
| `notify_worker.py` | email + SMS | module 01 |

## Rules

- [ ] Upload returns in **milliseconds**; processing runs behind it
- [ ] Retry with exponential backoff, 5 attempts, then dead-letter
- [ ] **A dead-lettered job is never silently discarded** - it surfaces on the admin screen
- [ ] Idempotency keys prevent duplicate side-effects on retry
- [ ] When a job finishes, push to the doctor portal over WebSocket

```bash
celery -A workers.celery_app worker -l info -Q ocr --concurrency=2
```

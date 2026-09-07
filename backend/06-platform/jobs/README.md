# Background Jobs

**Module:** 06 — Platform
**Team:** all 6 members contribute · **Lead this sprint:** _assign in standup_
**Path:** `backend/06-platform/jobs`

---

## What this is for

OCR takes seconds. The patient must never wait for it, and the doctor's screen must fill in as results land.

## What it does

- Queue and run OCR jobs
- Retry with backoff, then dead-letter — never silently lose a job
- Push to the doctor's screen when a job finishes

## What you build here

| File | Does |
|---|---|
| `queue.py` | job envelope, retry, dead-letter |
| `ocr_job.py` | document processing |
| `summary_job.py` | summary generation |
| `notify_job.py` | email and SMS |

## Pipeline position

```
IN    queued work
OUT   results written back, screens updated
```

**Depends on:** Redis + a worker
**Feeds:** modules 03, 04, 05

## Definition of done

- [ ] Upload returns in **milliseconds**; OCR runs behind it
- [ ] 5 retries with backoff, then dead-letter with an alert
- [ ] **A dead-lettered job is never silently discarded**
- [ ] The doctor's reports section fills in live as documents finish

## Reference

- `docs/ARCHITECTURE.md`

---

*Shared folder. Any of the six can add files here — leave a line in this README when you do,
so the next person knows what exists.*

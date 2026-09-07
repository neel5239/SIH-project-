# http/ — the HTTP plumbing every module shares

**Path:** `backend/06-platform/http/`

Each module owns its own `api.py` router. This folder holds the plumbing they all sit behind,
so six people are not each inventing their own conventions.

```
http/
├── middleware/     auth · request_id · errors · ratelimit
├── ws/             hub · doctor channel
└── mocks.py        fixture responses for MOCK mode
```

## Conventions — set once, never renegotiated

| | |
|---|---|
| Base path | `/api` |
| Auth | `Authorization: Bearer <jwt>` with `role` and `user_id` claims |
| Request id | `X-Request-ID` — generated if absent, echoed, on every log line |
| Errors | `{ "error": { "code", "message", "request_id" } }` |
| Async | POST returns `202 { job_id, poll_url }` and never blocks |

## Non-negotiables

- [ ] **Never PII in a path or query string.** Not a name, not a phone number, not a value.
- [ ] `role` and `user_id` come from the **token**, never from a request parameter
- [ ] A patient token reaches only that patient's own data; a doctor token only their patients
- [ ] **PII redaction filter in the logger from day 1**

## Mock mode

```bash
MOCK=02,03,04 docker compose up
```

Listed modules return fixtures from `06-platform/database/seed/`. Drop a number once that
module is real. **This is how nobody is blocked after day 1.**

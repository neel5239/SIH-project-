# API Client

One typed client for both applications, matching the backend routes.

| File | Covers |
|---|---|
| `client.js` | base fetch — auth header, request id, error shape, retry on 5xx |
| `auth.js` | module 01 |
| `questionnaire.js` | module 02 — start, answer, next question |
| `documents.js` | module 03 — quality check, upload, poll status |
| `doctor.js` | module 05 — patient list, the four sections, source replay, confirm |

- [ ] **Never PII in a URL** — enforce it here, not just by convention
- [ ] Upload calls return immediately; the client polls or listens for completion
- [ ] Errors surface a `code` the UI can act on, never a raw stack

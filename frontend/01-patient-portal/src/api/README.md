# api/ — this portal's backend calls

Wraps `04-shared/api/client.ts` and adds the **patient** token.

| File | Backend module | Endpoints |
|---|---|---|
| `client.ts` | — | base wrapper, patient token, error handling |
| `auth.ts` | **01-authentication** | login · OTP send/verify · refresh |
| `questionnaire.ts` | **02-questionnaire** | start · answer · next question · closing questions |
| `documents.ts` | **03-document-ocr** | quality check · upload · poll status |
| `records.ts` | **05-doctor-portal** | my visits, scoped to me |

## Rules

- [ ] **Never PII in a URL.** Enforce it here, not by convention.
- [ ] Speech and typing call the **same** `questionnaire.answer()` — the backend must not know which
- [ ] `documents.upload()` returns immediately; poll for status, never block the screen
- [ ] A patient token reaches **only** that patient's own data

# api/ — this portal's backend calls

Wraps `04-shared/api/client.ts` and adds the **doctor** token.

| File | Backend module | Endpoints |
|---|---|---|
| `client.ts` | — | base wrapper, doctor token, error handling |
| `auth.ts` | **01-authentication** | login · accept invite · refresh |
| `patients.ts` | **05-doctor-portal** | queue · the four sections for one patient · confirm |
| `sources.ts` | **04-summary-engine** + **03-document-ocr** | resolve a source tag → audio clip or document crop |
| `verify.ts` | **03-document-ocr** | confirm an item the OCR refused to guess |

## Rules

- [ ] A doctor token reaches **only** their own patients
- [ ] `sources.resolve()` must return fast enough that audio starts in **under 300 ms** — cache it
- [ ] An edit is optimistic with rollback; a failed save must be visible
- [ ] Nothing is written to the record until `patients.confirm()` is called

# WebSocket

Push, not poll. The doctor's screen must fill in as the patient finishes and as documents process.

| Channel | Payload |
|---|---|
| `/ws/doctor/{id}` | `patient_ready` · `documents_processed` · `summary_ready` · `emergency_flag` |

- [ ] The doctor's list updates with **no refresh**
- [ ] The reports section fills in live as OCR jobs finish
- [ ] An emergency flag arrives immediately and is impossible to miss
- [ ] Reconnect with backoff and replay what was missed

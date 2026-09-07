# ws/ - WebSocket channels

**Path:** `backend/06-platform/http/ws/`

Push, not poll. The doctor's screen must fill in as the patient finishes and as documents
process, without anyone pressing refresh.

| Channel | Payload |
|---|---|
| `/ws/doctor/{doctor_id}` | `patient_ready` - `documents_processed` - `summary_ready` - `red_flag` |

| File | Does |
|---|---|
| `hub.py` | connection registry + fan-out |
| `doctor.py` | the doctor channel endpoint |

## Rules

- [ ] The doctor's patient list updates with **no refresh**
- [ ] Section 4 (Reports) fills in **live** as OCR jobs finish
- [ ] A red flag arrives immediately and is impossible to miss
- [ ] Reconnect with backoff and replay what was missed
- [ ] **Fallback:** if the socket cannot connect, the portal polls every 10 s. Degraded, never broken.

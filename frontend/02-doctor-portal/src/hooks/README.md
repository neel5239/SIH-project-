# hooks/ — live data and edit plumbing

| File | Does |
|---|---|
| `useQueue.ts` | live patient list over `/ws/doctor/{id}`, emergency-flagged first |
| `usePatientView.ts` | fetch the four sections; **refresh as OCR results land** |
| `useSource.ts` | resolve a source tag → audio clip or crop, then cache it |
| `useEdit.ts` | optimistic edit with rollback on failure |

- [ ] The list updates with **no refresh** when a patient finishes their questionnaire
- [ ] Section ④ Reports fills in **progressively** as each document finishes
- [ ] A red flag arrives immediately, before sections ① and ② exist
- [ ] Reconnect with backoff; **fallback to a 10 s poll** if the socket cannot connect

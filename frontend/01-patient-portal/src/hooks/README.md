# hooks/ — logic kept out of the screens

So the screens stay about the patient.

| File | Does |
|---|---|
| `useIntake.ts` | submit a turn, receive the next question, resume after a break |
| `useCaptureQC.ts` | live camera loop → backend quality check → **spoken** hint |
| `useIdle.ts` | re-prompt at 20 s and 40 s, end gracefully at 90 s |
| `useOffline.ts` | buffer turns if the connection blips, replay on reconnect |

- [ ] State persists after **every** turn, not at the end
- [ ] Resume works after the patient walks away and comes back
- [ ] Capture QC stays under 150 ms per frame
- [ ] Idle handling never traps or scolds the patient

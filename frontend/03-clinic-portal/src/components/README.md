# components/ — the front desk, used hundreds of times a day

Every extra click here costs the clinic real throughput.

| File | Does |
|---|---|
| `PatientSearch.tsx` | by phone or name — **must return in under 300 ms** |
| `QuickRegister.tsx` ★ | name · phone · age · sex — nothing else |
| `AssignDoctor.tsx` ★ | suggested by department **and** language match |
| `TokenSlip.tsx` | printable token + room + doctor name |
| `QueueRow.tsx` | patient · doctor · **intake progress Q7/18** · elapsed |
| `RedFlagAlert.tsx` 🚨 | audible desk alert, must be acknowledged |
| `DoctorInviteRow.tsx` | name · email · sent/opened/accepted/expired · resend |
| `StatCard.tsx` | one number, large |

- [ ] Intake progress is visible so reception knows whether to wait for a patient
- [ ] The red-flag alert is **audible** and cannot be dismissed without acknowledging
- [ ] The queue board is readable from across a room

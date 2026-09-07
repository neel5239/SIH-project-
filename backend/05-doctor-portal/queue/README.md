# Doctor's Patient List

**Module:** 05 — Doctor Portal
**Team:** all 6 members contribute · **Lead this sprint:** _assign in standup_
**Path:** `backend/05-doctor-portal/queue`

---

## What this is for

What the doctor sees before opening any single patient: who is waiting, who has finished their questionnaire, and who needs to be seen first.

## What it does

- List today's patients for this doctor
- Show intake status: not started · in progress · complete
- **Sort emergency-flagged patients to the top**
- Update live as patients finish their questionnaire

## What you build here

| File | Does |
|---|---|
| `list.py` | today's patients |
| `status.py` | intake progress per patient |
| `priority.py` | emergency flags first |
| `realtime.py` | push when a patient's data is ready |

## Pipeline position

```
IN    doctor session
OUT   the patient list + live updates
```

**Depends on:** modules 02 and 04
**Feeds:** doctor portal frontend

## Definition of done

- [ ] A doctor sees **only their own patients**
- [ ] Emergency-flagged patients are at the top and visually distinct
- [ ] 'Data ready' arrives **without a refresh**
- [ ] Intake progress is visible — the doctor knows whether to wait

## Reference

- `docs/DOCTOR_PORTAL.md`

---

*Shared folder. Any of the six can add files here — leave a line in this README when you do,
so the next person knows what exists.*

# Section 1 — Basic Patient Information

**Module:** 05 — Doctor Portal
**Team:** all 6 members contribute · **Lead this sprint:** _assign in standup_
**Path:** `backend/05-doctor-portal/patient_info`

---

## What this is for

**The top of the doctor's screen.** Who is this person, and what did they come in saying.

## What it does

- Name, age, sex, contact
- Today's chief complaint in the patient's own words
- Previous visits with this doctor or clinic
- The emergency banner, if one fired — above everything else

## What you build here

| File | Does |
|---|---|
| `info.py` | demographics + contact |
| `complaint.py` | today's chief complaint, verbatim |
| `history.py` | previous visits |
| `banner.py` | the emergency banner slot |

## Pipeline position

```
IN    visit id + doctor session
OUT   the header block of the doctor's screen
```

**Depends on:** module 01, module 02
**Feeds:** doctor portal frontend

## Definition of done

- [ ] Readable in **three seconds** — this is a header, not a record
- [ ] The chief complaint is shown in the patient's own words, not paraphrased
- [ ] An emergency banner sits **above** this block and is impossible to miss

## Reference

- `docs/DOCTOR_PORTAL.md — section 1`

---

*Shared folder. Any of the six can add files here — leave a line in this README when you do,
so the next person knows what exists.*

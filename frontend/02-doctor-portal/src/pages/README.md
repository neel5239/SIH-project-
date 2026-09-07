# Doctor Portal — Pages

**Module:** Frontend — Doctor Portal
**Team:** all 6 members contribute · **Lead this sprint:** _assign in standup_
**Path:** `frontend/02-doctor-portal/src/pages`

---

## What this is for

Module 05 on the screen. Dense, structured, fast to scan — the opposite of the patient app.

## What it does

- Login, then the day's patient list
- Open a patient into the four-section view
- Edit and confirm

## What you build here

| File | Does |
|---|---|
| `Login.jsx` |  |
| `PatientList.jsx` | today's patients, emergency-flagged first, live |
| `PatientView.jsx` | ★★ the four sections, in order |
| `Profile.jsx` |  |

## Pipeline position

```
IN    doctor session
OUT   a reviewed, confirmed record
```

**Depends on:** `shared/api/doctor`
**Feeds:** the physician

## Definition of done

- [ ] The four sections render in the fixed order and never reorder
- [ ] The list updates without a refresh when a patient finishes
- [ ] Emergency-flagged patients are unmistakable

```
┌──────────────────────────────────────────┐
│ 🚨 EMERGENCY  chest pain + breathlessness│
│    rule CP-001 · priority                │
├──────────────────────────────────────────┤
│ ① BASIC INFORMATION                      │
│    Aarav · 42 · Male · +91 …             │
│    "Seene mein dard, do din se"           │
├──────────────────────────────────────────┤
│ ② SUMMARY                    ← read this │
│    Pressure-like central chest pain,     │
│    2 days, radiating to left arm,        │
│    with breathlessness.   [Patient]      │
│    Known diabetic.        [Rx 12/04/25]  │
│    Hb 10.2 ↓              [Lab 05/08/26] │
├──────────────────────────────────────────┤
│ ③ QUESTIONNAIRE          ← full Q&A      │
│    Q: Where is the pain?                 │
│    A: Centre of chest        🔊 spoken   │
│    Q: Does it spread?                    │
│    A: Left arm               🔊 spoken   │
│    …                                     │
├──────────────────────────────────────────┤
│ ④ REPORTS                                │
│    2025-04-12  Rx   Metformin 500 BD     │
│    2026-08-05  Lab  Hb 10.2 ↓            │
│    2026-08-05  ECG  sinus rhythm         │
│    ⚠ 1 line unreadable  [show the ink]   │
└──────────────────────────────────────────┘
```

## Reference

- `docs/DOCTOR_PORTAL.md`

---

*Shared folder. Any of the six can add files here — leave a line in this README when you do,
so the next person knows what exists.*

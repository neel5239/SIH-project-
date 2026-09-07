# PORTAL 02 — DOCTOR PORTAL

**Path:** `frontend/02-doctor-portal/`
**User:** a physician with two minutes who scans, does not read
**Port:** 3001  ·  **Theme:** CLINICAL — dense, structured, source-attributed
**Team:** all 6 members contribute. Assign a lead per sprint in standup.

**Everything this portal needs lives in this folder.** Its own API calls, its own screens, its
own components, its own hooks. The only thing outside it is `04-shared`.

---

## What this portal is for

One screen, four sections, in a **fixed order**. This is what the doctor opens when the
patient walks in.

**① basic information → ② summary → ③ questionnaire → ④ reports**

The order is a product decision. Do not change it. The summary sits above the questionnaire
deliberately — most doctors will read it and never scroll further, and that is the point.

---

## 🔌 CONNECTIONS — which backend module each screen talks to

```
   ┌────────────────────────────────────────────┐
   │        02-DOCTOR-PORTAL  (this)            │
   └────────────────────────────────────────────┘
        │          │            │           │
    src/auth   src/sections  src/       src/components
        │       ① ② ③ ④    components   source replay
        ▼          ▼            ▼           ▼
   backend/    backend/     backend/    backend/
   01-auth     05-doctor-   04-summary  03-document
               portal       -engine     -ocr
                            (source     (crops ·
                             replay)     verify)

              ┌──────────────┐        ┌──────────────┐
              │  04-shared   │        │  WebSocket   │
              └──────────────┘        │  live push   │
                                      └──────────────┘
```

### Calls these backend modules

| Screen folder | Backend module | What for |
|---|---|---|
| `src/auth/` | **01-authentication** | login, and `AcceptInvite` when a clinic added them |
| `src/pages/PatientList` | **05-doctor-portal** | today's patients, emergency-flagged first |
| `src/sections/` ① ② ③ ④ | **05-doctor-portal** | the four section payloads for one patient |
| `src/components/AudioReplay` | **04-summary-engine** | resolve a source tag → the patient's own audio |
| `src/components/ImageViewer` | **03-document-ocr** | resolve a source tag → the document crop |
| `src/components/VerifyChip` | **03-document-ocr** | confirm an item the OCR refused to guess |
| `src/components/EditableLine` | **04-summary-engine** | a doctor edit → stored as a correction |

### Receives pushed events

| Event | From backend | Effect on this screen |
|---|---|---|
| `red_flag` | **02-questionnaire** | patient jumps to the top of the list, **immediately** — before 03 and 04 have even run |
| `documents_processed` | **03-document-ocr** | section ④ Reports fills in **live**, per document |
| `summary_ready` | **04-summary-engine** | sections ① and ② appear |

All over `/ws/doctor/{id}`, handled in `src/hooks/useQueue.ts`.

**Fallback:** if the socket cannot connect, poll every 10 s. Degraded, never broken.

> **This is the only portal that writes back into the pipeline.** A doctor's correction returns
> to `03-document-ocr` (as an OCR training pair) or `04-summary-engine` (as a field correction).
> Nothing else in the system reverses direction.
>
> **Audio must start in under 300 ms** when a source tag is tapped. If it lags, the effect dies.

---

## What is inside this folder

```
02-doctor-portal/
├── README.md
├── package.json · vite.config.ts · tsconfig.json · Dockerfile · .env.example
│
└── src/
    ├── main.tsx · App.tsx · routes.tsx
    │
    ├── api/            its OWN calls — auth · patients · sources · verify
    ├── pages/          Login · AcceptInvite ★ · PatientList · PatientView ★★ · Profile
    ├── sections/       ★★ THE FOUR, IN FIXED ORDER
    │                       EmergencyBanner 🚨
    │                       BasicInfo       ①
    │                       Summary         ②  ← the doctor reads this
    │                       Questionnaire   ③
    │                       Reports         ④
    │                       ImagingPanel        quoted impression + attention terms
    ├── components/     SourceTag ★★ · AudioReplay ★★ · ImageViewer ★★
    │                   VerifyChip · ConflictRow · SeverityPill
    │                   EditableLine · ConfirmBar
    └── hooks/          useQueue · usePatientView · useSource · useEdit
```

**Every sub-folder has its own README.md.** Open the one you are working in.

---

## The rules for this portal

1. **The four sections render in fixed order and never reorder.**
2. **Every summary line carries a source tag.** `[Patient]` `[Rx 12/04/25]` `[Lab 05/08/26]`
3. **Tap a source → hear the patient, or see the ink.** Under 300 ms.
4. **A conflict renders as two lines with two sources.** Never merged.
5. **Unreadable items show the image**, never a confident guess.
6. **Nothing is saved to the record until the doctor confirms.**
7. Severity is encoded in **form** — stripe, chip, icon — not only in text.
8. The doctor **never types a clinic name** — the invite link carried it.

```
🚨 EMERGENCY  chest pain + breathlessness · rule CP-001
────────────────────────────────────────────────────
① Aarav · 42 · Male        "Seene mein dard, do din se"
────────────────────────────────────────────────────
② SUMMARY                              ← reads this
   Pressure-like central chest pain,
   radiating to left arm.      [Patient]
   Known diabetic.             [Rx 12/04/25]
   Hb 10.2 ↓                   [Lab 05/08/26]
────────────────────────────────────────────────────
③ QUESTIONNAIRE   Q: Where is the pain?
                  A: Centre of chest      🔊 spoken
────────────────────────────────────────────────────
④ REPORTS         2026-08-05  Lab  Hb 10.2 ↓
                  ⚠ 1 line unreadable  [show the ink]
────────────────────────────────────────────────────
              [ Edit ]    [ Confirm ]
```

---

## Run

```bash
cd frontend/02-doctor-portal
npm install
npm run dev          # http://localhost:3001
```

---

## Reference

- `frontend/README.md` — how the three portals fit together
- `frontend/04-shared/README.md` — the shared client, themes and strings
- `docs/ARCHITECTURE.md` — the full picture
- `backend/<module>/README.md` — the backend module behind each screen

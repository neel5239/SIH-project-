# FRONTEND

**Three portals. Two design languages. Everything a portal needs lives inside its own folder.**

---

## Structure — one folder per portal, nothing shared outside them

```
frontend/
│
├── 01-patient-portal/      ← everything the patient side needs
│   ├── README.md               ★ includes: which backend module each screen calls
│   ├── package.json · vite.config.ts · Dockerfile · .env.example
│   └── src/
│       ├── api/                its OWN backend calls
│       ├── auth/               ① login — phone + OTP is the primary path
│       ├── questionnaire/      ② SPEAK or TYPE, on every question
│       │   ├── speak/              SUB-MODULE A
│       │   └── type/               SUB-MODULE B
│       ├── documents/          ③ opens only if they said yes to reports
│       ├── records/            my visits · lab trends · audio recap
│       ├── components/         input primitives that work without literacy
│       ├── hooks/              intake · capture QC · idle · offline
│       └── a11y/               audio-first · contrast · proxy · privacy
│
├── 02-doctor-portal/       ← everything the doctor screen needs
│   ├── README.md
│   ├── package.json · vite.config.ts · Dockerfile · .env.example
│   └── src/
│       ├── api/                its OWN backend calls
│       ├── pages/              Login · AcceptInvite · PatientList · PatientView
│       ├── sections/           ★★ the four fixed sections
│       ├── components/         SourceTag · AudioReplay · ImageViewer · ConfirmBar
│       └── hooks/              queue · patient view · source · edit
│
├── 03-clinic-portal/       ← everything the clinic staff need
│   ├── README.md
│   ├── package.json · vite.config.ts · Dockerfile · .env.example
│   └── src/
│       ├── api/                its OWN backend calls
│       ├── pages/              Register · Dashboard · Doctors ★ · Reception ★ · QueueBoard
│       ├── components/         search · quick-register · assign · token · red-flag alert
│       └── hooks/              queue · search · invites · alert sound
│
└── 04-shared/              ← the ONLY shared folder
    ├── api/                    base client · error shape · generated types
    ├── ws/                     reconnecting socket · event vocabulary
    ├── ui/                     tokens · patient.css · clinical.css · primitives
    └── i18n/                   UI chrome strings only
```

**No shared `pages/`, `components/` or `hooks/` folder.** If a portal needs it, it is in that
portal. `04-shared` holds only what all three genuinely use: the API client, the socket, the
themes, and the UI strings.

---

## The three portals, and who uses each

| Portal | User | Port | Theme |
|---|---|---|---|
| **01-patient-portal** | a patient — possibly elderly, unable to read, first-time, in a noisy hall | 3000 | **PATIENT** — huge, spoken, icon-driven |
| **02-doctor-portal** | a physician with two minutes who scans, does not read | 3001 | **CLINICAL** — dense, structured, source-attributed |
| **03-clinic-portal** | a clinic administrator **and** a receptionist | 3002 | **CLINICAL** — dense, fast, one-click |

**The patient screen and the doctor screen must not look alike.** Both themes live in
`04-shared/ui/`. **Never mix them.**

```
PATIENT THEME                     CLINICAL THEME
huge type, huge buttons           dense, structured
high contrast                     four fixed sections
almost no typing                  a source tag on every line
audio before text                 tabular numerals
icons on every option             editable in place
64 px touch targets               fast to scan, not to read
```

---

## 🔌 Which portal talks to which backend module

```
   01-PATIENT-PORTAL          02-DOCTOR-PORTAL       03-CLINIC-PORTAL
          │                          │                      │
   ┌──────┼──────┬───────┐    ┌──────┼──────┐         ┌─────┼─────┐
   ▼      ▼      ▼       ▼    ▼      ▼      ▼         ▼     ▼     ▼
  01-    02-    03-     05-  01-    05-   04-+03-    01-   05-   06-
 auth  questn.  ocr   doctor auth doctor  sources   auth doctor platform
                     (own                (replay ·  (clinic (queue ·  (metrics)
                    records)              verify)   doctor  assign)
                                                    invite)

                    ┌──────────────────────────┐
                    │       04-shared          │
                    │  api · ws · ui · i18n    │
                    └──────────────────────────┘
```

| Portal | Backend modules it calls |
|---|---|
| **01-patient-portal** | 01-authentication · 02-questionnaire · 03-document-ocr · 05-doctor-portal *(own records)* |
| **02-doctor-portal** | 01-authentication · 05-doctor-portal · 04-summary-engine *(source replay)* · 03-document-ocr *(crops, verify)* |
| **03-clinic-portal** | 01-authentication *(clinic + doctor + receptionist accounts)* · 05-doctor-portal *(queue, assignment)* · 06-platform *(metrics)* |

**Each portal's README has a `🔌 CONNECTIONS` section** naming the exact backend module behind
every screen folder, and the events it receives pushed.

---

## Live events — who listens

| Event | From backend | 01 patient | 02 doctor | 03 clinic |
|---|---|---|---|---|
| `red_flag` | 02-questionnaire | shows the stop screen | 🚨 jumps to the top of the list | 🚨 audible desk alert |
| `intake_progress` | 02-questionnaire | — | — | `Q 7/18` on the queue row |
| `intake_complete` | 02-questionnaire | — | patient appears as ready | row flips to ready |
| `documents_processed` | 03-document-ocr | status chip updates | ④ Reports fills in **live** | — |
| `summary_ready` | 04-summary-engine | — | ① and ② appear | — |

The patient portal **polls** its own upload status. The doctor and clinic portals hold a
**WebSocket** — a patient's screen never needs to react to someone else's action.

**Fallback everywhere:** if the socket cannot connect, poll every 10 s. Degraded, never broken.

---

## The one rule about text

| | Comes from |
|---|---|
| **UI chrome** — buttons, labels, screen titles, error text | `04-shared/i18n/strings/` |
| **Clinical content** — questions, summaries, alerts, impressions | **the backend, at runtime** |

Confusing the two means a question gets translated twice, or a drug name gets translated at all.

---

## Rules that apply to all three portals

1. **Never show a diagnosis.** The backend will not send one; do not invent one in the UI either.
2. **Every clinical fact on the doctor's screen carries a source tag.**
3. **A conflict renders as two lines with two sources.** Never merged.
4. **Never PII in a URL.** Enforce it in `src/api/client.ts`, not by convention.
5. **Degrade, never crash.** A patient must never see a stack trace.
6. **Role scoping is server-side.** Hiding a button is not access control.

---

## Run

```bash
# each portal is independent
cd frontend/01-patient-portal && npm install && npm run dev    # :3000
cd frontend/02-doctor-portal  && npm install && npm run dev    # :3001
cd frontend/03-clinic-portal  && npm install && npm run dev    # :3002

# or all of them
docker compose up --build
```

| Portal | URL |
|---|---|
| Patient | http://localhost:3000 |
| Doctor | http://localhost:3001 |
| Clinic | http://localhost:3002 |
| Backend API docs | http://localhost:8000/docs |

---

## Build order

```
1  04-shared                api client · themes · error shape     ← first, everyone needs it
2  01-patient-portal        type/ path only, no speech            ← proves the flow end to end
3  02-doctor-portal         the four sections against fixtures
4  03-clinic-portal         reception desk, then doctor invites
5  01-patient-portal        add speak/ on top of the typed path
6  02-doctor-portal         source replay — tap to hear, tap to see
7  polish · accessibility pass · demo rehearsal
```

**Build the typed path before the spoken path.** It proves the whole flow without depending on
a speech provider, and it is the accessibility fallback anyway.

---

## Reference

| | |
|---|---|
| Full architecture | `docs/ARCHITECTURE.md` |
| Every endpoint | `docs/API_SPEC.md` |
| Backend module behind a screen | `backend/<module>/README.md` |
| Your portal's spec and its connections | the `README.md` in that portal's folder |

# PORTAL 01 — PATIENT PORTAL

**Path:** `frontend/01-patient-portal/`
**User:** a patient — possibly elderly, unable to read, first-time, standing in a noisy hall
**Port:** 3000  ·  **Theme:** PATIENT — huge, spoken, icon-driven
**Team:** all 6 members contribute. Assign a lead per sprint in standup.

**Everything this portal needs lives in this folder.** Its own API calls, its own screens, its
own components, its own hooks. The only thing outside it is `04-shared`.

---

## What this portal is for

The whole patient side, on screen. Login, then the questionnaire by **speaking or typing**,
then document upload if they brought papers, then done.

It also holds "my records" — where the patient later sees their own visits, lab trends and an
audio recap in their own language. For most of them that is the first time they have ever held
their own medical record in a readable form.

**It must not look like a chat app.**

---

## 🔌 CONNECTIONS — which backend module each screen talks to

```
   ┌────────────────────────────────────────────┐
   │        01-PATIENT-PORTAL  (this)           │
   └────────────────────────────────────────────┘
        │            │             │         │
    src/auth   src/questionnaire  src/    src/records
        │            │         documents      │
        ▼            ▼             ▼          ▼
   backend/     backend/      backend/    backend/
   01-auth      02-question-  03-document 05-doctor-
                naire         -ocr        portal
                                          (patient-scoped read)

              ┌──────────────┐
              │  04-shared   │  ← api client · ws · themes · strings
              └──────────────┘
```

### Calls these backend modules

| Screen folder | Backend module | What for |
|---|---|---|
| `src/auth/` | **01-authentication** | phone + OTP (primary), email, external providers |
| `src/questionnaire/` | **02-questionnaire** | start · submit an answer · get the next question · the two closing questions |
| `src/documents/` | **03-document-ocr** | live quality check · upload · poll status |
| `src/records/` | **05-doctor-portal** | the patient's own visits, scoped to them |

Speech and typing both hit the **same** `02-questionnaire` endpoint. The backend does not know
which door was used, and must not need to.

### Receives pushed events

**None.** This portal polls its own upload status; it does not hold a WebSocket.

A patient's screen never needs to react to someone else's action.

> **`src/documents/` only opens if the patient answered yes** to the two closing questions in
> `src/questionnaire/ReportCheck.tsx`. If they said no to both, the flow goes straight to `Done`.
>
> **Upload never blocks.** The backend returns immediately and processes in the background; this
> portal shows a status chip and lets the patient keep adding files.

---

## What is inside this folder

```
01-patient-portal/
├── README.md
├── package.json · vite.config.ts · tsconfig.json · Dockerfile · .env.example
│
└── src/
    ├── main.tsx · App.tsx · routes.tsx
    │
    ├── api/                its OWN calls — auth · questionnaire · documents · records
    ├── auth/               ① Login · PhoneOtp ★ · EmailLogin · Providers · Verify
    ├── questionnaire/      ② Start · Question · Progress · ReportCheck ★ · Confirm
    │   │                       · RedFlagStop ★★
    │   ├── speak/              ★ SUB-MODULE A — Recorder · Listening · useSpeech
    │   └── type/               ★ SUB-MODULE B — Options · BodyMap · FaceScale · FreeText
    ├── documents/          ③ Upload · Camera ★ · FileRow · DocList · Done
    ├── records/            MyVisits · VisitDetail · LabTrends · AudioRecap
    ├── components/         MicButton · OptionCard · ProgressDots · SkipButton · BigButton
    ├── hooks/              useIntake · useCaptureQC · useIdle · useOffline
    └── a11y/               audioFirst · contrast · proxyMode · privacy
```

**Every sub-folder has its own README.md.** Open the one you are working in.

---

## The rules for this portal

1. **One question per screen.**
2. **Spoken before it is read.** Every screen plays audio before requiring input.
3. **SPEAK or TYPE on every question.** A complete questionnaire must be possible with
   **zero voice input**.
4. **Nothing mandatory.** Skip is always visible.
5. **Can stop at any time** — the doctor still gets whatever was captured.
6. **`RedFlagStop` never names a disease.** It says the symptoms may need urgent attention and
   points at the triage desk.
7. **Touch targets at least 64 px.** Every option has an icon recognisable **without** its label.
8. **Test standing up, at arm's length, in a bright room.** That is the real condition.

```
┌───────────────────────────────┐
│         Namaste 🙏            │
│   Aapko aaj kya problem hai?  │
│                               │
│      🎤  SPEAK                │
│      👆  TYPE                 │
│                               │
│      [ 🔊 Sunaye ]            │
│   ●●●●○○○   ~3 min left       │
└───────────────────────────────┘
```

---

## Run

```bash
cd frontend/01-patient-portal
npm install
npm run dev          # http://localhost:3000
```

---

## Reference

- `frontend/README.md` — how the three portals fit together
- `frontend/04-shared/README.md` — the shared client, themes and strings
- `docs/ARCHITECTURE.md` — the full picture
- `backend/<module>/README.md` — the backend module behind each screen

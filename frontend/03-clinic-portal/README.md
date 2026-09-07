# PORTAL 03 — CLINIC PORTAL

**Path:** `frontend/03-clinic-portal/`
**User:** two different people — the clinic administrator, and the receptionist at the front desk
**Port:** 3002  ·  **Theme:** CLINICAL — dense, fast, one-click
**Team:** all 6 members contribute. Assign a lead per sprint in standup.

**Everything this portal needs lives in this folder.** Its own API calls, its own screens, its
own components, its own hooks. The only thing outside it is `04-shared`.

---

## What this portal is for

Two users share this app, and the role decides the landing page.

**The administrator** registers the clinic and **adds its doctors by name and email**. Each
doctor gets an invite, sets a password, and lands on a dashboard already bound to that clinic —
they never type a clinic name.

**The receptionist** works the front desk: find or quick-register a walk-in patient, assign them
to a doctor, issue a token, and point them at the questionnaire. **That assignment is what gives
every intake a destination** — without it, a completed questionnaire has nowhere to go.

---

## 🔌 CONNECTIONS — which backend module each screen talks to

```
   ┌────────────────────────────────────────────┐
   │        03-CLINIC-PORTAL  (this)            │
   │                                            │
   │   ADMIN view          RECEPTION view       │
   │   Dashboard           Reception ★★         │
   │   Doctors ★★          QueueBoard           │
   │   Settings                                 │
   └────────────────────────────────────────────┘
        │              │              │
   src/api/clinic  src/api/     src/api/stats
   src/api/doctors reception         │
        │              │              │
        ▼              ▼              ▼
   backend/        backend/       backend/
   01-auth         05-doctor-     06-platform
   (clinic +       portal         (metrics)
    doctor +       (queue ·
    receptionist    assign)
    accounts)

              ┌──────────────┐        ┌──────────────┐
              │  04-shared   │        │  WebSocket   │
              └──────────────┘        │  live queue  │
                                      └──────────────┘
```

### Calls these backend modules

| Screen | Backend module | What for |
|---|---|---|
| `pages/Register` | **01-authentication** | clinic self-registration + the first admin account |
| `pages/Doctors` ★★ | **01-authentication** | create a doctor by name + email → send a signed invite → track status |
| `pages/Reception` ★★ | **05-doctor-portal** | patient search · quick-register · assign to a doctor · issue a token |
| `pages/QueueBoard` | **05-doctor-portal** | the live queue for the whole clinic |
| `pages/Dashboard` | **06-platform** | operational metrics — patients today, average wait, intake completion |
| `pages/Settings` | **01-authentication** | departments · OPD hours · languages offered |

### Receives pushed events

| Event | From backend | Effect on this screen |
|---|---|---|
| `red_flag` | **02-questionnaire** | 🚨 audible alert at the desk, patient pinned to the top of the queue |
| `intake_progress` | **02-questionnaire** | `Q 7/18` on the queue row, so reception knows whether to wait |
| `intake_complete` | **02-questionnaire** | the row flips to "ready for the doctor" |

All over `/ws/clinic/{clinic_id}`, handled in `src/hooks/useQueue.ts`.

**The board must update with no refresh.** An emergency surface that polls looks broken.

> ### ⚠ Backend note — read this before starting
>
> There is **no dedicated `07-clinic` backend module.** The clinic portal is served by two
> existing ones:
>
> - **`01-authentication`** — clinic, doctor and receptionist accounts, the invite flow, roles
> - **`05-doctor-portal`** — the patient queue, assignment, and tokens
>
> If the team decides the clinic domain has grown enough to deserve its own module, create
> `backend/07-clinic/` and move those endpoints. **Decide that before writing the API calls**,
> not after.

---

## What is inside this folder

```
03-clinic-portal/
├── README.md
├── package.json · vite.config.ts · tsconfig.json · Dockerfile · .env.example
│
└── src/
    ├── main.tsx · App.tsx · routes.tsx    role decides the landing page
    │
    ├── api/            its OWN calls — clinic · doctors · reception · stats
    ├── pages/
    │   ├── Register.tsx        ★ clinic self-registration
    │   ├── Login.tsx
    │   ├── Dashboard.tsx       ADMIN — today's numbers
    │   ├── Doctors.tsx         ★★ ADMIN — add doctor by NAME + EMAIL, track invites
    │   ├── Reception.tsx       ★★ RECEPTION — search / register / assign / token
    │   ├── QueueBoard.tsx      live queue, red flags pinned
    │   └── Settings.tsx
    ├── components/     PatientSearch · QuickRegister ★ · AssignDoctor ★
    │                   TokenSlip · QueueRow · RedFlagAlert 🚨
    │                   DoctorInviteRow · StatCard
    └── hooks/          useQueue · useSearch · useInvites · useAlertSound
```

**Every sub-folder has its own README.md.** Open the one you are working in.

---

## The rules for this portal

1. **Adding a doctor takes name + email and nothing else.**
2. **Invite status is visible** — sent · opened · accepted · expired — and re-send is one click.
3. **Quick-registering a patient takes under 20 seconds of typing.** Name, phone, age, sex.
4. **Assignment suggests doctors by department AND by a language the patient speaks.**
5. **The receptionist screen shows NO clinical content.** Identity, doctor, department, token.
   A request for a summary must return **403**.
6. **The queue board updates with no refresh**, and a red flag is **audible** and must be
   acknowledged.
7. Search returns in under 300 ms. This desk is used hundreds of times a day under time pressure —
   every extra click costs the clinic real throughput.

```
ADMIN — DOCTORS                RECEPTION — DESK
+ Add doctor                   🔍 search phone / name
  name  ____________               ▼
  email ____________           quick-register (20 s)
  [ Send invite ]                  ▼
                               assign to doctor
Dr. Sharma  accepted ✅        (dept + language match)
Dr. Iyer    opened   ⏳            ▼
Dr. Khan    expired  ⚠ resend  Token 47 · Room 3 · Dr. Sharma

        LIVE QUEUE — no refresh
  ┌──────────────────────────────────────┐
  │ 🚨 47 · Dr.Sharma · RED FLAG CP-001  │ pinned
  │ 48 · Dr.Sharma · intake Q7/18        │
  │ 49 · Dr.Iyer   · waiting             │
  └──────────────────────────────────────┘
```

---

## Run

```bash
cd frontend/03-clinic-portal
npm install
npm run dev          # http://localhost:3002
```

---

## Reference

- `frontend/README.md` — how the three portals fit together
- `frontend/04-shared/README.md` — the shared client, themes and strings
- `docs/ARCHITECTURE.md` — the full picture
- `backend/<module>/README.md` — the backend module behind each screen

# MODULE 01 — AUTHENTICATION

**Path:** `backend/01-authentication/`
**Team:** all 6 members contribute. Assign a lead per sprint in standup.
**Everything this module needs lives in this folder.** No shared `api/`, `core/` or
`contracts/` folder — if this module needs it, it is here.

---

## What this module is for

Establish who this person is, using established authentication services rather than a
password scheme we invent ourselves — email, phone with a one-time code, and external identity
providers.

**Everything downstream depends on this.** No module runs without a valid session, and the role
on that session decides whether a request sees patient data or doctor data.

---

## 🔌 CONNECTIONS — who calls this, and what it calls next

```
      PATIENT / DOCTOR arrives
                 │
                 ▼
      ┌────────────────────────┐
      │   01-AUTHENTICATION    │  ◄── you are here
      │   email · phone+OTP    │
      │   · external providers │
      └───────────┬────────────┘
                  │  session { user_id, role }
                  ▼
      ┌────────────────────────┐
      │   02-QUESTIONNAIRE     │  (patient)
      │   05-DOCTOR-PORTAL     │  (doctor)
      └────────────────────────┘
```

### Called by

**Nothing.** This is the entry point. Every other module is reached *through* it.

### Calls next

| Next module | When |
|---|---|
| **02-questionnaire** | role = `PATIENT` → straight into the questionnaire |
| **05-doctor-portal** | role = `DOCTOR` → straight to their patient list |

It also **provides a dependency to every module**: `require_role()` and `current_user()` are
imported from `01-authentication.schemas` by all five others.

### What it hands over

```json
{
  "session": {
    "user_id": "c7d8e9f0-1111-4222-8333-444455556666",
    "role": "PATIENT",
    "patient_id": "a1b2c3d4-…",
    "access_token": "eyJhbGciOi…",
    "refresh_token": "…",
    "expires_in": 1800
  }
}
```

> **This module is called on every single request**, not just at login — the middleware in
> `06-platform/http/middleware/auth.py` verifies the token and attaches `user_id` and `role`
> before any route body runs.

---

## What is inside this folder

```
01-authentication/
├── README.md
├── api.py                 register · verify · login · OTP · providers · refresh
├── schemas.py             ★ Session · Role · User — what other modules import
├── models.py              users · sessions · invites · verification tokens
├── service.py             orchestration
├── config.py              token lifetimes, OTP rules, provider list
│
├── email_auth/            register · verify link · login · password reset
├── phone_auth/            ★ OTP over SMS — the PRIMARY patient path
├── oauth_providers/       external identity providers, behind one interface
├── session/               JWT, refresh rotation, roles, guards, revocation
└── tests/                 the negative cases matter more than the positive ones
```

**Every sub-folder has its own README.md.** Open the one you are working in.

| File | Does |
|---|---|
| `api.py` | this module's FastAPI router — mounted by `06-platform/app.py` |
| `schemas.py` | **what this module exposes to other modules** — the only thing they may import |
| `models.py` | this module's own database tables |
| `service.py` | orchestration — ties the sub-parts together |
| `config.py` | this module's settings, read from env |

---

## Import rules

```
✅  from platform_runtime import storage, cache, logging     # shared runtime is fine
✅  import 01-authentication.schemas                                  # another module's PUBLIC schemas
❌  import 01-authentication.service                                  # another module's internals
❌  import 01-authentication.models                                   # another module's tables
```

**A module may import another module's `schemas.py` and nothing else.** That file is the
contract. Everything else in this folder is private.

---

## Six rules every module obeys

1. **Never diagnose.** No disease name, no treatment, no drug recommendation — anywhere.
2. **Never state a fact without saying where it came from.**
3. **Never merge conflicting information.** Show both; the doctor decides.
4. **Never block the patient.** Any question is skippable; a partial record is still valuable.
5. **Degrade, never crash.** The patient must never see a stack trace.
6. **The doctor makes the clinical decision.** We collect, structure and present.

> ### The thing to remember
>
> **Most patients will not remember a password.** Phone plus a one-time code is the path almost
> all of them will use. Make it fast and forgiving: re-send after 30 seconds, accept the code
> with or without spaces, work on a weak connection.

---

## Reference

- `backend/README.md` — how the six modules fit together
- `docs/ARCHITECTURE.md` — the full picture
- the `README.md` inside each sub-folder of this module

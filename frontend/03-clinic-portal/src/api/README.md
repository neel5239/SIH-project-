# api/ — this portal's backend calls

Wraps `04-shared/api/client.ts` and adds the **clinic-staff** token.

| File | Backend module | Endpoints |
|---|---|---|
| `client.ts` | — | base wrapper, staff token, error handling |
| `clinic.ts` | **01-authentication** | clinic registration · settings · staff accounts |
| `doctors.ts` | **01-authentication** | create doctor · send invite · invite status · roster · deactivate |
| `reception.ts` | **05-doctor-portal** | patient search · quick-register · assign · token · queue |
| `stats.ts` | **06-platform** | operational metrics |

## Rules

- [ ] **A receptionist request for clinical content must return 403.** Do not paper over it in the UI.
- [ ] `doctors.invite()` sends name + email only — the clinic binding is server-side
- [ ] `reception.search()` returns in under 300 ms, debounced client-side
- [ ] Cross-clinic requests return 403 — scoping comes from the token, never a parameter

> **Backend note:** there is no `07-clinic` module. These calls land on **01-authentication**
> (accounts, invites, roles) and **05-doctor-portal** (queue, assignment). If the clinic domain
> grows, create `backend/07-clinic/` — but decide that before writing these calls.

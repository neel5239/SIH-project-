# Sessions, Tokens & Roles

**Module:** 01 — Authentication
**Team:** all 6 members contribute · **Lead this sprint:** _assign in standup_
**Path:** `backend/01-authentication/session`

---

## What this is for

Two very different actors share one API: the patient and the doctor. The token is what keeps a patient out of another patient's record.

## What it does

- Issue a short-lived access token and a rotating refresh token
- Embed `role` and `user_id` as claims — never read them from a query parameter
- Revoke on logout, on password change, on role change
- Guard every route by role

## What you build here

| File | Does |
|---|---|
| `jwt.py` | sign / verify / claims |
| `refresh.py` | rotation + reuse detection |
| `roles.py` | PATIENT · DOCTOR · ADMIN |
| `guards.py` | require_role · require_self dependencies |
| `revoke.py` | denylist + cascade |

## Pipeline position

```
IN    verified credentials from any of the three paths above
OUT   `{ access_token, refresh_token, role }`
```

**Depends on:** Redis (denylist)
**Feeds:** every authenticated route in the system

## Definition of done

- [ ] Access token ≤ 30 minutes; refresh rotates on every use
- [ ] **Refresh-token reuse triggers a full revoke** — a stolen token is detectable
- [ ] **A patient can read only their own records** — enforced in the data layer, not just the route
- [ ] A doctor sees only patients routed to them

## Reference

- `docs/API_SPEC.md — Auth`

---

*Shared folder. Any of the six can add files here — leave a line in this README when you do,
so the next person knows what exists.*

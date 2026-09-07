# Email Authentication

**Module:** 01 — Authentication
**Team:** all 6 members contribute · **Lead this sprint:** _assign in standup_
**Path:** `backend/01-authentication/email_auth`

---

## What this is for

Email sign-up and sign-in for staff and for patients who have an email address. Standard, boring, and it must be exactly right — everything else in the product sits on top of it.

## What it does

- Register with email + password, send a verification link
- Login, logout, forgot-password, reset-password
- Block login until the email is verified
- Passwords hashed with argon2 or bcrypt — never stored, never logged

## What you build here

| File | Does |
|---|---|
| `register.py` | email + password sign-up |
| `verify.py` | signed verification link, single-use, 24 h expiry |
| `login.py` | credential check, constant-time compare |
| `password.py` | hashing, strength rules, reset flow |
| `mailer.py` | email adapter — provider-swappable |

## Pipeline position

```
IN    email + password
OUT   a verified user + a session
```

**Depends on:** `session/`, an SMTP provider
**Feeds:** patient app, doctor portal

## Definition of done

- [ ] Password never appears in a log, a URL, or an API response
- [ ] Verification link is signed, single-use, and expires
- [ ] Failed login is rate-limited by email **and** by IP
- [ ] Reset link invalidates all existing sessions for that user

## Reference

- `docs/API_SPEC.md — Auth`

---

*Shared folder. Any of the six can add files here — leave a line in this README when you do,
so the next person knows what exists.*

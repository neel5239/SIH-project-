# Patient App — Login

**Module:** Frontend — Patient App
**Team:** all 6 members contribute · **Lead this sprint:** _assign in standup_
**Path:** `frontend/01-patient-portal/src/auth`

---

## What this is for

Module 01 on the screen. Phone plus a code is the primary path; email and external providers are alternatives.

## What it does

- Phone number + OTP, large and forgiving
- Email and password as an alternative
- External provider buttons where enabled

## What you build here

| File | Does |
|---|---|
| `Login.jsx` | the choice of method |
| `PhoneOtp.jsx` | ★ the primary path |
| `EmailLogin.jsx` |  |
| `Providers.jsx` | external auth buttons |
| `Verify.jsx` | code entry, auto-read where the platform allows |

## Pipeline position

```
IN    phone or email
OUT   a session
```

**Depends on:** `shared/api/auth`
**Feeds:** the patient

## Definition of done

- [ ] Large buttons, large text, minimal typing
- [ ] Re-send allowed after 30 seconds
- [ ] The code is accepted with or without spaces
- [ ] Works on a low-end phone on a weak connection

## Reference

- `docs/PATIENT_FLOW.md — step 1`

---

*Shared folder. Any of the six can add files here — leave a line in this README when you do,
so the next person knows what exists.*

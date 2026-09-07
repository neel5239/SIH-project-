# Phone / OTP Authentication

**Module:** 01 — Authentication
**Team:** all 6 members contribute · **Lead this sprint:** _assign in standup_
**Path:** `backend/01-authentication/phone_auth`

---

## What this is for

Most of our patients will not remember a password. Phone number plus a one-time code is the only login they will reliably complete — and it is the primary path for the patient side.

## What it does

- Send a 6-digit code over SMS
- Verify it, then issue a session
- Rate-limit hard — 3 sends per number per 10 minutes, 5 verify attempts per code
- Burn the code on first successful use

## What you build here

| File | Does |
|---|---|
| `send_otp.py` | generate, hash, store with a 5-minute TTL, send |
| `verify_otp.py` | constant-time compare, attempt counter, burn on success |
| `sms.py` | SMS gateway adapter — provider-swappable |
| `ratelimit.py` | per phone, per IP, per device |

## Pipeline position

```
IN    phone number (E.164, +91…)
OUT   `{ txn_id }` then a session on verify
```

**Depends on:** Redis, an SMS provider
**Feeds:** patient app — **the primary patient login**

## Definition of done

- [ ] OTP is **hashed** at rest, never stored in plain text
- [ ] Constant-time comparison — no timing oracle
- [ ] Burned after one successful use
- [ ] **The OTP never appears in a log line, a URL, or a response body**
- [ ] Works on a 2G connection — the SMS is the only network hop that matters

This is the login almost every patient will use. Make it fast and forgiving: allow re-send after 30 s, accept the code with or without spaces, and auto-read it on Android where possible.

## Reference

- `docs/API_SPEC.md — Auth`

---

*Shared folder. Any of the six can add files here — leave a line in this README when you do,
so the next person knows what exists.*

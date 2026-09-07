# Configuration & Secrets

**Module:** 06 — Platform
**Team:** all 6 members contribute · **Lead this sprint:** _assign in standup_
**Path:** `backend/06-platform/config`

---

## What this is for

One place where every setting and credential lives, validated at boot so a missing key fails loudly on startup rather than quietly at 2 a.m.

## What it does

- Load and validate settings from the environment
- Fail startup on a missing required value
- Keep provider choices swappable — speech, OCR, SMS, email, auth

## What you build here

| File | Does |
|---|---|
| `settings.py` | typed settings, validated at boot |
| `providers.py` | which speech / OCR / SMS / email / auth provider is active |
| `logging.py` | structured logs with a **PII redaction filter** |
| `health.py` | `/health` and `/ready` |

## Pipeline position

```
IN    environment variables
OUT   a validated settings object
```

**Depends on:** —
**Feeds:** everything

## Definition of done

- [ ] A missing required variable fails **startup**, loudly
- [ ] **A PII redaction filter in the logger from day 1** — no name, phone, OTP or clinical text in a log line
- [ ] `/ready` returns 200 only when the database and every model are actually reachable
- [ ] Swapping a speech or OCR provider is a config change, not a code change

## Reference

- ``.env.example``

---

*Shared folder. Any of the six can add files here — leave a line in this README when you do,
so the next person knows what exists.*

# Auth Tests

**Module:** 01 — Authentication
**Team:** all 6 members contribute · **Lead this sprint:** _assign in standup_
**Path:** `backend/01-authentication/tests`

---

## What this is for

Auth bugs are silent and catastrophic. Test the negative cases harder than the positive ones.

## What it does

- All three login paths
- Every negative case below

## What you build here

| File | Does |
|---|---|
| `test_email.py` |  |
| `test_phone.py` |  |
| `test_oauth.py` |  |
| `test_roles.py` |  |

## Pipeline position

```
IN    —
OUT   pass / fail
```

**Depends on:** pytest
**Feeds:** CI

## Definition of done

- [ ] Patient A cannot read patient B's record
- [ ] An unverified email cannot log in
- [ ] OTP brute force is blocked after 5 attempts
- [ ] An expired or reused verification link is rejected
- [ ] OAuth callback with a bad state parameter is rejected

## Reference

- `docs/API_SPEC.md`

---

*Shared folder. Any of the six can add files here — leave a line in this README when you do,
so the next person knows what exists.*

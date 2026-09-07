# Doctor Portal Tests

**Module:** 05 — Doctor Portal
**Team:** all 6 members contribute · **Lead this sprint:** _assign in standup_
**Path:** `backend/05-doctor-portal/tests`

---

## What this is for

Access boundaries and the four-section contract.

## What it does

- Section order and content
- Access isolation
- Source replay

## What you build here

| File | Does |
|---|---|
| `test_sections.py` |  |
| `test_access.py` |  |
| `test_replay.py` |  |

## Pipeline position

```
IN    —
OUT   pass / fail
```

**Depends on:** pytest
**Feeds:** CI

## Definition of done

- [ ] Sections render in the fixed order: info → summary → questionnaire → reports
- [ ] Doctor A cannot open doctor B's patient
- [ ] A source tag resolves to the correct audio clip or document crop

## Reference

- `docs/DOCTOR_PORTAL.md`

---

*Shared folder. Any of the six can add files here — leave a line in this README when you do,
so the next person knows what exists.*

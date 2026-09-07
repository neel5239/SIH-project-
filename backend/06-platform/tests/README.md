# Platform Tests

**Module:** 06 — Platform
**Team:** all 6 members contribute · **Lead this sprint:** _assign in standup_
**Path:** `backend/06-platform/tests`

---

## What this is for

The contracts between modules, and the end-to-end path.

## What it does

- Contract tests
- Full patient → doctor path
- Failure drills

## What you build here

| File | Does |
|---|---|
| `test_contracts.py` | every module's output matches the agreed shape |
| `test_e2e.py` | login → questionnaire → documents → summary → doctor screen |
| `test_failures.py` | OCR down · model down · storage down |

## Pipeline position

```
IN    —
OUT   pass / fail
```

**Depends on:** pytest
**Feeds:** CI

## Definition of done

- [ ] The full path runs end to end with real modules
- [ ] **Contract test runs on every push.** A mismatch fails the build.
- [ ] Every failure drill ends with a usable screen, never a stack trace

## Reference

- `docs/DATA_CONTRACTS.md`

---

*Shared folder. Any of the six can add files here — leave a line in this README when you do,
so the next person knows what exists.*

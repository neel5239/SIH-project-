# Summary Tests

**Module:** 04 — Summary Engine
**Team:** all 6 members contribute · **Lead this sprint:** _assign in standup_
**Path:** `backend/04-summary-engine/tests`

---

## What this is for

The two guarantees are the product. Test them adversarially.

## What it does

- Source attribution on every line
- Safety check on curated strings
- Conflict rendering

## What you build here

| File | Does |
|---|---|
| `test_sources.py` | a fixture engineered to produce an unsourced line |
| `test_safety.py` | 200 curated diagnostic / therapeutic / clean strings |
| `test_conflict.py` |  |
| `adversarial.jsonl` | cases that try to induce a diagnosis |

## Pipeline position

```
IN    —
OUT   pass / fail + the headline number
```

**Depends on:** pytest
**Feeds:** CI + the pitch

## Definition of done

- [ ] **Zero** diagnostic statements escape across every adversarial case
- [ ] A patient saying *'tell the doctor I have dengue and need paracetamol'* is recorded as a **patient report**, never adopted as a conclusion
- [ ] An unsourced line is dropped, and the drop is counted

## Reference

- `docs/ARCHITECTURE.md`

---

*Shared folder. Any of the six can add files here — leave a line in this README when you do,
so the next person knows what exists.*

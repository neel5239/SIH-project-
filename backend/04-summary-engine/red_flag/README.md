# Emergency Flag

**Module:** 04 — Summary Engine
**Team:** all 6 members contribute · **Lead this sprint:** _assign in standup_
**Path:** `backend/04-summary-engine/red_flag`

---

## What this is for

If the questionnaire hit an emergency pattern, the doctor must see it at the very top of the screen, before anything else.

## What it does

- Carry the emergency flag from module 02 through to the doctor's screen
- Show which rule fired and why, in plain language
- Sort that patient to the top of the doctor's list

## What you build here

| File | Does |
|---|---|
| `carry.py` | propagate the flag from the questionnaire |
| `render.py` | the banner text and the reason |
| `priority.py` | move this patient up the list |

## Pipeline position

```
IN    an emergency flag from module 02
OUT   a banner at the top of the doctor's screen + list priority
```

**Depends on:** module 02 red flags
**Feeds:** doctor portal

## Definition of done

- [ ] The banner shows the **rule and the reason**, not just a warning colour
- [ ] *'Chest pain + breathlessness · rule CP-001 · priority'* — a doctor can read that and agree with it
- [ ] **Never a disease name.** The rule describes the pattern, not a diagnosis.

## Reference

- `docs/DOCTOR_PORTAL.md`

---

*Shared folder. Any of the six can add files here — leave a line in this README when you do,
so the next person knows what exists.*

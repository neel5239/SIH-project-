# Summary Generator

**Module:** 04 — Summary Engine
**Team:** all 6 members contribute · **Lead this sprint:** _assign in standup_
**Path:** `backend/04-summary-engine/generator`

---

## What this is for

Produces the short summary that sits **above** the full questionnaire on the doctor's screen. A doctor with two minutes reads this first and may never scroll further.

## What it does

- Write a concise clinical summary from the aggregated facts
- Keep it to what a doctor can read in about twenty seconds
- Attach a source to every line
- Fall back to a plain template if the model is unavailable

## What you build here

| File | Does |
|---|---|
| `generate.py` | the constrained generation call |
| `schema.py` | the fixed summary shape — the model fills it, it cannot write free prose |
| `template.py` | fallback renderer over the raw answers |
| `sources.py` | attach the source tag to every line |

## Pipeline position

```
IN    the aggregated fact set
OUT   a short summary, every line sourced
```

**Depends on:** an LLM runtime
**Feeds:** `safety/` then the doctor portal

## Definition of done

- [ ] The summary is **phrasing, not reasoning.** It restates facts it was handed; it adds nothing.
- [ ] Every line carries a source tag: `[Patient answer]` `[Prescription 12/04/2025]` `[Lab report 05/08/2026]`
- [ ] **A line with no source is dropped, not shown.** A flagged unsourced claim is still a claim on the doctor's screen.
- [ ] **The template fallback is not optional** — models fail at the worst moments, and the demo must still render

## Reference

- `docs/DOCTOR_PORTAL.md`

---

*Shared folder. Any of the six can add files here — leave a line in this README when you do,
so the next person knows what exists.*

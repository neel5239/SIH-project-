# Aggregator

**Module:** 04 — Summary Engine
**Team:** all 6 members contribute · **Lead this sprint:** _assign in standup_
**Path:** `backend/04-summary-engine/aggregator`

---

## What this is for

Everything from the patient side arrives here: the questionnaire answers and the extracted documents. This folder puts them into one clinical structure before anything is written for a doctor.

## What it does

- Collect the questionnaire answers from module 02
- Collect the extracted entities and timeline from module 03
- Map both into standard clinical sections
- Detect where the patient's answer and a document disagree — and **surface both, never merge**

## What you build here

| File | Does |
|---|---|
| `collect.py` | pull both sources for one visit |
| `sections.py` | map into: chief complaint · history · past illness · medicines · allergies · investigations |
| `conflict.py` | patient said no diabetes, prescription shows Metformin → show BOTH |
| `units.py` | unify units and drug names across the two sources |

## Pipeline position

```
IN    questionnaire answers + extracted documents
OUT   one aligned, fully sourced fact set
```

**Depends on:** modules 02 and 03
**Feeds:** `generator/`

## Definition of done

- [ ] Every fact keeps a record of **where it came from** — patient interview, or which document, or which date
- [ ] **Never a merged value when the two sources disagree.** Show both lines and flag it.
- [ ] A visit with no documents still produces a complete fact set from the questionnaire alone

## Reference

- `docs/DOCTOR_PORTAL.md`

---

*Shared folder. Any of the six can add files here — leave a line in this README when you do,
so the next person knows what exists.*

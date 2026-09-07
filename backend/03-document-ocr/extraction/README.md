# Clinical Extraction & Timeline

**Module:** 03 — Document OCR
**Team:** all 6 members contribute · **Lead this sprint:** _assign in standup_
**Path:** `backend/03-document-ocr/extraction`

---

## What this is for

Entities alone are useless. `Metformin`, `500`, `mg`, `BD` as four loose tokens tells a doctor nothing. **The relations, and the order in time, are the value.**

## What it does

- Link entities into whole clinical facts
- Resolve the date of every document — explicit, then inferred, then patient-stated. **Never invent one.**
- Order everything chronologically and remove duplicates
- Score confidence and route low-confidence items to human verification

## What you build here

| File | Does |
|---|---|
| `relations.py` | medicine → strength → frequency → duration |
| `dates.py` | date resolution, undated bucket |
| `dedup.py` | same report photographed twice, or a photocopy plus the original |
| `timeline.py` | the patient's story in order |
| `confidence.py` | the verification gate |
| `verify_queue.py` | items the doctor must confirm |

## Pipeline position

```
IN    extracted entities from all three pipelines
OUT   a chronological, deduplicated, confidence-scored record
```

**Depends on:** —
**Feeds:** module 04 · doctor portal reports section

## Definition of done

- [ ] Three documents across three dates order correctly and a duplicate is removed
- [ ] No date resolvable → 'undated', **never guessed**
- [ ] Trend detection: *'HbA1c 9.2 → 8.6, improving'*
- [ ] A drug-interaction warning **states the fact and never advises**. 'Warfarin and Aspirin both present' — never 'stop the aspirin'.

## Reference

- `docs/ARCHITECTURE.md`

---

*Shared folder. Any of the six can add files here — leave a line in this README when you do,
so the next person knows what exists.*

# Section 2 — Summary

**Module:** 05 — Doctor Portal
**Team:** all 6 members contribute · **Lead this sprint:** _assign in standup_
**Path:** `backend/05-doctor-portal/summary_view`

---

## What this is for

**Directly under the basic information, and above the full questionnaire.** This is what the doctor actually reads. If they read nothing else, this must be enough.

## What it does

- Serve the generated summary from module 04
- Show a source tag on every line
- Let the doctor tap a source to hear the patient or see the document
- Let the doctor edit any line — the correction is stored

## What you build here

| File | Does |
|---|---|
| `summary.py` | fetch the summary for this visit |
| `source.py` | resolve a source tag → audio clip or document crop |
| `edit.py` | doctor edits a line → stored as a correction |
| `confirm.py` | doctor accepts the summary |

## Pipeline position

```
IN    visit id
OUT   the summary block with sources
```

**Depends on:** module 04
**Feeds:** doctor portal frontend

## Definition of done

- [ ] **Readable in about twenty seconds** — time it
- [ ] Every line has a source tag the doctor can tap
- [ ] Audio starts in **under 300 ms**, or the effect is lost
- [ ] **The summary is a draft.** The doctor can edit or reject any part of it.

Screen order, top to bottom: **basic info → SUMMARY → full questionnaire → reports.** The summary sits above the questionnaire deliberately — most doctors will never scroll past it, and that is fine.

## Reference

- `docs/DOCTOR_PORTAL.md — section 2`

---

*Shared folder. Any of the six can add files here — leave a line in this README when you do,
so the next person knows what exists.*

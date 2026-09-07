# Section 3 — The Questionnaire the Patient Submitted

**Module:** 05 — Doctor Portal
**Team:** all 6 members contribute · **Lead this sprint:** _assign in standup_
**Path:** `backend/05-doctor-portal/questionnaire_view`

---

## What this is for

**Under the summary.** The complete set of questions and answers, exactly as the patient gave them. The doctor drops into this when the summary is not enough.

## What it does

- Show every question and its answer, in the order they were asked
- Mark how each answer was given — spoken or tapped
- Mark answers a relative gave on the patient's behalf
- Let the doctor replay the audio for any spoken answer

## What you build here

| File | Does |
|---|---|
| `questions.py` | the full Q&A list |
| `grouping.py` | group by section: complaint · history · medicines · allergies · lifestyle |
| `replay.py` | play the recording for a spoken answer |
| `input_mode.py` | mark spoken vs tapped vs answered-by-relative |

## Pipeline position

```
IN    visit id
OUT   the full questionnaire block
```

**Depends on:** module 02
**Feeds:** doctor portal frontend

## Definition of done

- [ ] **Nothing is hidden.** Every question the patient was asked and every answer they gave.
- [ ] Skipped questions are shown as skipped, not silently omitted
- [ ] Tap a spoken answer → hear the patient say it
- [ ] An answer given by a relative is visibly marked — its reliability is different

## Reference

- `docs/DOCTOR_PORTAL.md — section 3`

---

*Shared folder. Any of the six can add files here — leave a line in this README when you do,
so the next person knows what exists.*

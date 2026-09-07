# The Two Closing Questions

**Module:** 02 — Patient Questionnaire
**Team:** all 6 members contribute · **Lead this sprint:** _assign in standup_
**Path:** `backend/02-questionnaire/report_check`

---

## What this is for

After the clinical questions, exactly two questions decide whether module 03 opens at all.

## What it does

- Ask: **'Do you have any previous reports?'**
- Ask: **'Do you have any previous prescriptions?'**
- If either is yes → open the document upload module
- If both are no → end the patient side and send everything to the doctor

## What you build here

| File | Does |
|---|---|
| `ask.py` | the two questions, spoken and tappable |
| `route.py` | yes → module 03 · no → finish |
| `summary_prompt.py` | read the answers back: 'this is what I recorded, is it correct?' |

## Pipeline position

```
IN    the completed clinical questionnaire
OUT   a routing decision + the confirmed answer set
```

**Depends on:** `question_engine/`
**Feeds:** module 03 (if yes) · module 04 (always)

## Definition of done

- [ ] Both questions are spoken and tappable — yes / no, nothing more
- [ ] **Yes to either one opens the upload screen.** No to both ends the patient journey cleanly.
- [ ] Before finishing, read the answers back to the patient in their language — the last chance to correct us
- [ ] A patient who says no can still upload later from their portal

```
           questionnaire complete
                    │
                    ▼
     "Do you have previous reports?"
     "Do you have previous prescriptions?"
                    │
         ┌──────────┴──────────┐
         ▼                     ▼
        YES                    NO
         │                     │
         ▼                     ▼
    MODULE 03            patient side ends
    upload documents           │
         │                     │
         └──────────┬──────────┘
                    ▼
            send to the doctor
```

## Reference

- `docs/PATIENT_FLOW.md — step 3`

---

*Shared folder. Any of the six can add files here — leave a line in this README when you do,
so the next person knows what exists.*

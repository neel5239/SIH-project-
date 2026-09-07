# TYPE — touch and text sub-module

**Module:** 02 — Patient Questionnaire
**Team:** all 6 members contribute · **Lead this sprint:** _assign in standup_
**Path:** `backend/02-questionnaire/type_module`

---

## What this is for

**Sub-module B of two.** The patient answers by tapping or typing. This is the fallback for a noisy room, a shy patient, a speech failure — and the path a literate patient may simply prefer.

## What it does

- Render every question as tappable option cards with icons
- Accept free text where the question needs it
- Provide a body diagram so a patient can point instead of naming the site
- Provide a face scale so pain can be rated without reading a number

## What you build here

| File | Does |
|---|---|
| `options.py` | render the allowed answers as tappable cards |
| `freetext.py` | handle typed answers |
| `body_map.py` | tap where it hurts |
| `scales.py` | face scale for severity, duration chips |
| `validate.py` | normalise a tapped or typed answer into the same shape as a spoken one |

## Pipeline position

```
IN    tap or typed text + the current question
OUT   the patient's answer, **identical shape to the speech path**
```

**Depends on:** —
**Feeds:** `question_engine/`

## Definition of done

- [ ] **A complete questionnaire is possible with zero voice input**
- [ ] Every closed question has an icon recognisable **without** its label
- [ ] Touch targets at least 64 px
- [ ] The answer shape is identical to the speech path — the question engine must not care which was used

Speech and type are two doors into the same room. The question engine sees one answer format either way.

## Reference

- `docs/PATIENT_FLOW.md — step 2`

---

*Shared folder. Any of the six can add files here — leave a line in this README when you do,
so the next person knows what exists.*

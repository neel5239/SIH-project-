# Patient App — Questionnaire

**Module:** Frontend — Patient App
**Team:** all 6 members contribute · **Lead this sprint:** _assign in standup_
**Path:** `frontend/01-patient-portal/src/questionnaire`

---

## What this is for

Module 02 on the screen. **Two doors into the same room:** speak, or tap. The patient chooses, and can switch at any time.

## What it does

- Offer SPEAK or TYPE on every single question
- Speak the question aloud before showing it
- Show progress so the patient can see the end coming
- Ask the two closing questions about reports and prescriptions

## What you build here

| File | Does |
|---|---|
| `Start.jsx` | 🎤 SPEAK  /  👆 TYPE  —  the choice, spoken aloud |
| `speak/Recorder.jsx` | ★ big mic button with a live level meter |
| `speak/Listening.jsx` | visual feedback that we heard them |
| `type/Options.jsx` | ★ icon cards, thumb-sized |
| `type/BodyMap.jsx` | tap where it hurts |
| `type/FaceScale.jsx` | six faces instead of a number |
| `Question.jsx` | one question, both input paths, always |
| `Progress.jsx` | how much is left |
| `ReportCheck.jsx` | ★ the two closing questions |
| `Confirm.jsx` | read the answers back before finishing |

## Pipeline position

```
IN    the current question from the backend
OUT   the patient's answer
```

**Depends on:** `shared/api/questionnaire`
**Feeds:** the patient

## Definition of done

- [ ] **Both input methods on every question.** Switching mid-questionnaire loses nothing.
- [ ] Every question is spoken before it is read
- [ ] A complete questionnaire is possible **without speaking a word**
- [ ] Progress is always visible
- [ ] Before finishing, the answers are read back for confirmation

```
          ┌─────────────────────────┐
          │   Aapko kya problem hai? │
          │                          │
          │   🎤 SPEAK    👆 TYPE    │
          │                          │
          │   [🔊 sunaye]  [skip]    │
          │   ●●●●○○○  ~3 min left   │
          └─────────────────────────┘
```

## Reference

- `docs/PATIENT_FLOW.md — step 2 and 3`

---

*Shared folder. Any of the six can add files here — leave a line in this README when you do,
so the next person knows what exists.*

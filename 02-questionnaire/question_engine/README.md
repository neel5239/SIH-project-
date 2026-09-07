# Question Engine

**Module:** 02 — Patient Questionnaire
**Team:** all 6 members contribute · **Lead this sprint:** _assign in standup_
**Path:** `backend/02-questionnaire/question_engine`

---

## What this is for

Decides what to ask next. A doctor taking a history does not read a form top to bottom — each answer changes the next question. This reproduces that structure.

## What it does

- Hold the patient's answers as structured state — **the application holds it, not the model**
- Branch on the chief complaint into the matching question flow
- Stop when enough has been asked, or when the patient wants to stop
- Watch for emergency patterns while it asks

## What you build here

| File | Does |
|---|---|
| `engine.py` | the state machine |
| `flows/` | YAML question flows — chest pain · fever · cough · abdominal · headache |
| `branch.py` | complaint → flow selection |
| `state.py` | the live structured patient state |
| `extract.py` | turn a free answer into a structured value |
| `red_flags.py` | deterministic emergency rules — NOT a model |
| `complete.py` | when the questionnaire ends |
| `resume.py` | patient stopped and came back |

## Pipeline position

```
IN    an answer from either sub-module
OUT   the next question, or 'complete'
```

**Depends on:** `speech_module/` `type_module/`
**Feeds:** `report_check/`, then module 04

## Definition of done

- [ ] Branching lives in **YAML, not Python** — a clinician can read it and the team can change the interview without touching code
- [ ] **Five complaint flows fully built.** Five perfected beats forty half-built.
- [ ] **The safety rules are deterministic.** A clinician must be able to read the rule that fired and agree with it.
- [ ] **The system never names a disease.** On an emergency pattern it says the symptoms may need urgent attention and flags it for the doctor.
- [ ] Any question is skippable. The questionnaire always ends. Whatever was captured is kept.

```
AI may interpret and communicate.
Rules determine safety.
Structured data stores the answers.
The doctor makes the clinical decision.
```

## Reference

- `docs/PATIENT_FLOW.md`

---

*Shared folder. Any of the six can add files here — leave a line in this README when you do,
so the next person knows what exists.*

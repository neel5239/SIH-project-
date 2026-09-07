# Questionnaire Tests

**Module:** 02 — Patient Questionnaire
**Team:** all 6 members contribute · **Lead this sprint:** _assign in standup_
**Path:** `backend/02-questionnaire/tests`

---

## What this is for

Scenario fixtures that double as demo scripts.

## What it does

- Every flow end to end
- Both input paths
- Every emergency rule

## What you build here

| File | Does |
|---|---|
| `test_flows.py` |  |
| `test_speech_path.py` |  |
| `test_type_path.py` |  |
| `test_red_flags.py` |  |
| `scenario_chest_pain.json` | the hero scenario |
| `scenario_fever.json` |  |

## Pipeline position

```
IN    —
OUT   pass / fail
```

**Depends on:** pytest
**Feeds:** CI + demo

## Definition of done

- [ ] Speech path and type path produce the **identical** answer set for the same scenario
- [ ] A complete questionnaire runs with zero voice input
- [ ] Every emergency rule fires on its positive fixture and not on its negative one
- [ ] **Get a doctor to read the flow YAML.** One hour, enormous credibility.

## Reference

- `docs/PATIENT_FLOW.md`

---

*Shared folder. Any of the six can add files here — leave a line in this README when you do,
so the next person knows what exists.*

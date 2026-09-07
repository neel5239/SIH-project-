# MODULE 04 — SUMMARY ENGINE

**Path:** `backend/04-summary-engine/`
**Team:** all 6 members contribute. Assign a lead per sprint in standup.
**Everything this module needs lives in this folder.** No shared `api/`, `core/` or
`contracts/` folder — if this module needs it, it is here.

---

## What this module is for

Everything from the patient side arrives here and becomes **one short summary a doctor can
read in twenty seconds** — with a source on every line, and a safety check that guarantees
nothing diagnostic ever reaches the screen.

This module sits between the patient side and the doctor side, and it is where the two
guarantees of the product are enforced.

---

## 🔌 CONNECTIONS — who calls this, and what it calls next

```
   02-QUESTIONNAIRE      03-DOCUMENT-OCR
        answers              structured items
           │                       │
           └───────────┬───────────┘
                       ▼
      ┌────────────────────────────┐
      │    04-SUMMARY-ENGINE       │  ◄── you are here
      │                            │
      │  aggregate                 │
      │  conflict → SHOW BOTH      │
      │  generate short summary    │
      │  ★ source check            │
      │  ★ safety check            │
      └─────────────┬──────────────┘
                    │  summary + sources + red flag
                    ▼
           05-DOCTOR-PORTAL
```

### Called by

| Module | When | Condition |
|---|---|---|
| **02-questionnaire** | when the questionnaire ends | **ALWAYS** — even a partial one |
| **03-document-ocr** | when every document has finished | **ONLY IF** the patient uploaded any |

It waits for **both**, but proceeds on a timeout if OCR is still running — a summary from the
questionnaire alone is better than no summary.

### Calls next

| Next module | When |
|---|---|
| **05-doctor-portal** | as soon as the summary is generated and has passed both checks |

It also **reads from 02 and 03** rather than being pushed to — it pulls their `schemas.py`
outputs for the visit.

### What it hands over

```json
{
  "visit_id": "…",
  "summary": {
    "paragraph": "Pressure-like central chest pain, 2 days, radiating to the left arm, with breathlessness. Known diabetic. Haemoglobin 10.2 g/dL is below the reference range.",
    "lines": [
      { "text": "Chest pain, 2 days",
        "source": { "kind": "patient_answer", "audio_ref": "…", "start_ms": 4200 } },
      { "text": "Metformin 500 mg BD",
        "source": { "kind": "document", "document_id": "…", "date": "2025-04-12" } }
    ]
  },
  "red_flags": [
    { "severity": "LOW", "test": "Haemoglobin", "value": 10.2,
      "range": "13.0–17.0",
      "message": "Haemoglobin: 10.2 g/dL — below the reference range (13.0–17.0)." }
  ],
  "conflicts": [
    { "patient_said": "no diabetes",
      "document_says": "Metformin 500 mg BD on prescription 12/04/2025" }
  ],
  "safety_checked": true,
  "diagnostic_statements_emitted": 0
}
```

> **This module never calls back to the patient side.** It is a one-way transform. If it needs
> something that is missing, it renders what it has and marks the gap — it does not ask the
> patient another question.

---

## What is inside this folder

```
04-summary-engine/
├── README.md
├── api.py                 generate · fetch
├── schemas.py             ★ ClinicalSummary · SourceTag — what 05 imports
├── models.py              summaries · sources · doctor corrections
├── service.py             aggregate → generate → source-check → safety-check
├── config.py              LLM settings, safety mode
│
├── aggregator/            combine both sources · conflicts, never merged
├── generator/             the short summary that sits above the questionnaire
├── safety/                ★ blocks diagnostic and treatment language · fails closed
├── red_flag/              carries the emergency banner through from module 02
└── tests/                 adversarial cases that try to induce a diagnosis
```

**Every sub-folder has its own README.md.** Open the one you are working in.

| File | Does |
|---|---|
| `api.py` | this module's FastAPI router — mounted by `06-platform/app.py` |
| `schemas.py` | **what this module exposes to other modules** — the only thing they may import |
| `models.py` | this module's own database tables |
| `service.py` | orchestration — ties the sub-parts together |
| `config.py` | this module's settings, read from env |

---

## Import rules

```
✅  from platform_runtime import storage, cache, logging     # shared runtime is fine
✅  import 04-summary-engine.schemas                                  # another module's PUBLIC schemas
❌  import 04-summary-engine.service                                  # another module's internals
❌  import 04-summary-engine.models                                   # another module's tables
```

**A module may import another module's `schemas.py` and nothing else.** That file is the
contract. Everything else in this folder is private.

---

## Six rules every module obeys

1. **Never diagnose.** No disease name, no treatment, no drug recommendation — anywhere.
2. **Never state a fact without saying where it came from.**
3. **Never merge conflicting information.** Show both; the doctor decides.
4. **Never block the patient.** Any question is skippable; a partial record is still valuable.
5. **Degrade, never crash.** The patient must never see a stack trace.
6. **The doctor makes the clinical decision.** We collect, structure and present.

> ### The thing to remember
>
> **The summary is phrasing, not reasoning.** It restates facts it was handed and adds nothing.
> Every line carries where it came from, and **any line that cannot say where it came from is
> dropped before the doctor ever sees it.**

---

## Reference

- `backend/README.md` — how the six modules fit together
- `docs/ARCHITECTURE.md` — the full picture
- the `README.md` inside each sub-folder of this module

# MODULE 02 — PATIENT QUESTIONNAIRE

**Path:** `backend/02-questionnaire/`
**Team:** all 6 members contribute. Assign a lead per sprint in standup.
**Everything this module needs lives in this folder.** No shared `api/`, `core/` or
`contracts/` folder — if this module needs it, it is here.

---

## What this module is for

Take the patient's clinical history. **Two sub-modules give two ways to answer the same
questions:** speak, or type. The patient picks either and can switch at any time.

At the end, two questions decide whether module 03 opens at all.

---

## 🔌 CONNECTIONS — who calls this, and what it calls next

```
      01-AUTHENTICATION
                 │  session { role: PATIENT }
                 ▼
      ┌────────────────────────┐
      │   02-QUESTIONNAIRE     │  ◄── you are here
      │  ┌──────┐  ┌────────┐  │
      │  │SPEAK │  │  TYPE  │  │
      │  └──┬───┘  └───┬────┘  │
      │     └────┬─────┘       │
      │     question engine    │
      │     ⚠ red-flag rules   │
      └───────────┬────────────┘
                  │
        "Do you have previous reports?"
        "Do you have previous prescriptions?"
                  │
        ┌─────────┴─────────┐
       YES                  NO
        │                   │
        ▼                   │
  03-DOCUMENT-OCR           │
        │                   │
        └─────────┬─────────┘
                  ▼
        04-SUMMARY-ENGINE   (always)
```

### Called by

| Module | When |
|---|---|
| **01-authentication** | immediately after a patient logs in |

### Calls next

| Next module | When | Condition |
|---|---|---|
| **03-document-ocr** | after the two closing questions | **ONLY IF** the patient answered yes to reports **or** prescriptions |
| **04-summary-engine** | after the questionnaire ends | **ALWAYS** — even if the patient skipped everything |
| **05-doctor-portal** | the moment a red flag fires | **ONLY IF** an emergency rule fired — it jumps the queue immediately, without waiting for the rest |

### What it hands over

```json
{
  "visit_id": "…",
  "answers": [
    { "key": "complaint.text", "value": "seene mein dard",
      "input_mode": "speak", "answered_by": "self",
      "source": { "kind": "patient_answer", "audio_ref": "…", "start_ms": 4200 } }
  ],
  "patient_state": { "complaint": "chest pain", "duration_days": 2, "…": "…" },
  "red_flag": {
    "fired": true, "rule_id": "CP-001",
    "reason": "Chest pain with breathlessness"
  },
  "has_documents": true,
  "end_reason": "red_flag"
}
```

> **The red flag does not wait.** If an emergency rule fires mid-questionnaire, this module
> notifies **05-doctor-portal** straight away, before 03 and 04 have run. The doctor sees the
> alert while the patient is still at the screen.
>
> **A partial questionnaire still flows onward.** If the patient stops, times out, or triggers
> an abort, whatever was captured still goes to 04.

---

## What is inside this folder

```
02-questionnaire/
├── README.md
├── api.py                 start · answer · next question · closing questions
├── schemas.py             ★ Answer · PatientState · RedFlag — what 04 imports
├── models.py              questionnaire sessions · answers · audio refs · red flags
├── service.py             routes an answer through speak OR type, then the engine
├── config.py              speech provider, time budget, thresholds
│
├── speech_module/         ★ SUB-MODULE A — record · transcribe · translate · speak aloud
├── type_module/           ★ SUB-MODULE B — icon cards · body map · face scale
├── question_engine/       what to ask next · patient state · emergency rules
│   └── flows/                 chest_pain · fever · cough · abdominal · headache · red_flags
├── report_check/          ★ the two closing questions that open or skip module 03
└── tests/                 scenario fixtures that double as demo scripts
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
✅  import 02-questionnaire.schemas                                  # another module's PUBLIC schemas
❌  import 02-questionnaire.service                                  # another module's internals
❌  import 02-questionnaire.models                                   # another module's tables
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
> **Speak and type are two doors into the same room.** The question engine sees one answer
> format either way — it must never care which door was used. And a complete questionnaire
> must be possible **without speaking a single word.**

---

## Reference

- `backend/README.md` — how the six modules fit together
- `docs/ARCHITECTURE.md` — the full picture
- the `README.md` inside each sub-folder of this module

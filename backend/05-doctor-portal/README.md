# MODULE 05 — DOCTOR PORTAL

**Path:** `backend/05-doctor-portal/`
**Team:** all 6 members contribute. Assign a lead per sprint in standup.
**Everything this module needs lives in this folder.** No shared `api/`, `core/` or
`contracts/` folder — if this module needs it, it is here.

---

## What this module is for

One screen, four sections, in a fixed order. This is what the doctor opens when the patient
walks in.

**The order is a product decision — do not change it:**
① basic information → ② **summary** → ③ questionnaire → ④ reports

---

## 🔌 CONNECTIONS — who calls this, and what it calls next

```
   01-AUTH        02-QUESTIONNAIRE     03-OCR      04-SUMMARY
   doctor          full Q&A            documents     summary
   session             │                   │            │
      │                └─────────┬─────────┘            │
      └──────────────────────────┼──────────────────────┘
                                 ▼
              ┌──────────────────────────────────┐
              │      05-DOCTOR-PORTAL            │  ◄── you are here
              │                                  │
              │  🚨 emergency banner             │
              │  ① basic information             │
              │  ② SUMMARY        ← reads this   │
              │  ③ questionnaire                 │
              │  ④ reports                       │
              │     [ Edit ]  [ Confirm ]        │
              └──────────────────┬───────────────┘
                                 │
                        doctor confirms
                                 ▼
                    stored · visible to the patient

              ═══ END OF THE PIPELINE ═══
```

### Called by

| Module | When | What it sends |
|---|---|---|
| **01-authentication** | doctor logs in | the session, and the doctor's patient list |
| **02-questionnaire** | **immediately** when a red flag fires | jumps this patient to the top, before 03 and 04 have run |
| **02-questionnaire** | when the questionnaire ends | the full Q&A for section ③ |
| **03-document-ocr** | **live**, as each document finishes | fills section ④ progressively |
| **04-summary-engine** | when the summary passes both checks | sections ① and ② |

### Calls next

| Next module | When |
|---|---|
| **03-document-ocr** | the doctor confirms an unreadable item → written back as a correction and a training pair |
| **04-summary-engine** | the doctor edits a summary line → stored as a correction |
| — | otherwise **nothing.** This is the end of the pipeline. |

### What it hands over

```json
{
  "visit_id": "…",
  "reviewed": true,
  "reviewed_by": "dr_sharma",
  "reviewed_at": "2026-09-03T14:31:02+05:30",
  "corrections": [
    { "target": "04-summary-engine", "field": "drugs[1]",
      "generated": "Telmisartan 40 OD", "corrected": "Telmisartan 40 BD" },
    { "target": "03-document-ocr", "item_id": "…",
      "was": null, "corrected": "Metformin 500 mg BD",
      "training_pair_stored": true }
  ],
  "doctor_note": "…"
}
```

> **This module receives from four others and is the only one the doctor touches.**
>
> It is also the only module that **writes back** — a doctor's correction returns to 03 or 04
> so the system measurably improves. Nothing else in the pipeline reverses direction.

---

## What is inside this folder

```
05-doctor-portal/
├── README.md
├── api.py                 patient list · the four sections · source replay · edit · confirm
├── schemas.py             ★ the four section payloads the frontend renders
├── models.py              doctor reviews · confirmations · notes
├── service.py             assemble the four sections for one patient
├── config.py              portal settings
│
├── queue/                 today's patients, emergency-flagged first, live
├── patient_info/          ① basic information — the header
├── summary_view/          ② summary — above the questionnaire, on purpose
├── questionnaire_view/    ③ the full Q&A the patient submitted
├── reports_view/          ④ documents · values · imaging · unreadable items
└── tests/                 section order and access boundaries
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
✅  import 05-doctor-portal.schemas                                  # another module's PUBLIC schemas
❌  import 05-doctor-portal.service                                  # another module's internals
❌  import 05-doctor-portal.models                                   # another module's tables
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
> **The summary sits above the questionnaire deliberately.** Most doctors will read it and never
> scroll further — that is the entire point of the product.
>
> **Nothing is saved to the record until the doctor confirms.**

---

## Reference

- `backend/README.md` — how the six modules fit together
- `docs/ARCHITECTURE.md` — the full picture
- the `README.md` inside each sub-folder of this module

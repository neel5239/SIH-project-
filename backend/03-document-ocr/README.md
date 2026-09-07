# MODULE 03 — DOCUMENT OCR

**Path:** `backend/03-document-ocr/`
**Team:** all 6 members contribute. Assign a lead per sprint in standup.
**Everything this module needs lives in this folder.** No shared `api/`, `core/` or
`contracts/` folder — if this module needs it, it is here.

---

## What this module is for

The patient uploads everything they brought — handwritten prescriptions, lab and blood
reports, sonography, CT, MRI, X-ray, ECG. Each type takes a different pipeline.

**This module only opens if the patient said yes** to the two closing questions in module 02.
When it finishes, the patient side is done.

---

## 🔌 CONNECTIONS — who calls this, and what it calls next

```
      02-QUESTIONNAIRE
                 │
        "yes, I have reports"
                 │
                 ▼
      ┌────────────────────────┐
      │   03-DOCUMENT-OCR      │  ◄── you are here
      │                        │
      │  prescriptions  (TrOCR)│
      │  lab reports (PaddleOCR)
      │  sonography · CT · MRI │
      │  X-ray · ECG           │
      └───────────┬────────────┘
                  │  structured items + timeline
                  ▼
        04-SUMMARY-ENGINE

  ═══ PATIENT SIDE ENDS HERE ═══
```

### Called by

| Module | When | Condition |
|---|---|---|
| **02-questionnaire** | after the two closing questions | **ONLY IF** the patient answered yes to reports or prescriptions |
| **05-doctor-portal** | a doctor confirms an unreadable item | writes a correction back into this module |

### Calls next

| Next module | When |
|---|---|
| **04-summary-engine** | when every uploaded document has finished processing |
| **05-doctor-portal** | live, as **each** document finishes — the Reports section fills in progressively, it does not wait for the last file |

### What it hands over

```json
{
  "visit_id": "…",
  "documents": [
    { "document_id": "…", "document_type": "lab_report",
      "report_date": "2026-08-05", "status": "DONE" }
  ],
  "items": [
    { "item_type": "lab_value",
      "payload": { "test_name": "Haemoglobin", "value": 10.2, "unit": "g/dL",
                   "ref_low": 13.0, "ref_high": 17.0 },
      "confidence": 0.96, "conf_band": "AUTO",
      "source": { "kind": "document", "page": 1, "bbox": [412,588,260,34] } },

    { "item_type": "medicine",
      "payload": { "name": null, "raw_ocr_guess": "Melformn 50?" },
      "confidence": 0.41, "conf_band": "ABSTAIN",
      "needs_verification": true,
      "source": { "kind": "document", "page": 2, "crop_ref": "…" } }
  ],
  "timeline": [ { "date": "2025-04-12", "text": "Metformin 500 mg BD started" } ],
  "unreadable_count": 1
}
```

> **This module is asynchronous.** Upload returns in milliseconds; OCR runs in the background
> via `06-platform/jobs_runtime`. Module 04 waits for completion, but module 05 is pushed each
> result as it lands, so the doctor's Reports section fills in live.
>
> **If the patient said no to both closing questions, this module never runs at all** — 02 goes
> straight to 04.

---

## What is inside this folder

```
03-document-ocr/
├── README.md
├── OCR_MODULE.md          ★ the full hybrid-OCR specification (4,900 lines)
├── api.py                 quality check · upload · status · verify · original · crop
├── schemas.py             ★ Document · LabValue · Medicine · ImagingReport — what 04 imports
├── models.py              documents · extracted items · verify queue
├── service.py             the whole OCR pipeline in order
├── config.py              OCR engines, DPI, confidence thresholds
│
├── upload/                camera and gallery capture, quality check, async
├── classifier/            which kind of document is this
├── handwritten_prescription/  ★ TrOCR + formulary constraint — cannot invent a drug
├── lab_report/            ★ PaddleOCR table-aware — our strongest demo
├── imaging_reports/       sonography · CT · MRI · X-ray · ECG — reads the IMPRESSION
├── extraction/            relations · dates · dedup · timeline · confidence
└── tests/                 the labelled corpus and the benchmark
    └── corpus/
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
✅  import 03-document-ocr.schemas                                  # another module's PUBLIC schemas
❌  import 03-document-ocr.service                                  # another module's internals
❌  import 03-document-ocr.models                                   # another module's tables
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

> ### Two boundaries we state out loud
>
> **We read the radiologist's report. We never interpret the scan image.**
>
> **On handwriting:** *knowing that it cannot read a line is a stronger and safer result than a
> confident wrong drug name.*

---

## Reference

- `backend/README.md` — how the six modules fit together
- `docs/ARCHITECTURE.md` — the full picture
- the `README.md` inside each sub-folder of this module

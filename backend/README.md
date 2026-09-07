# BACKEND

**Stack:** Python 3.11 · FastAPI · PostgreSQL 16 · Redis · Celery · MinIO/S3
**Six modules. Six team members. Everything a module needs lives inside that module's folder.**

---

## Structure — one folder per module, nothing shared outside them

```
backend/
│
├── 01-authentication/      ← everything auth needs is IN HERE
│   ├── README.md               ★ includes: who calls this, what it calls next
│   ├── api.py                  its own router
│   ├── schemas.py              ★ what other modules may import
│   ├── models.py               its own tables
│   ├── service.py              orchestration
│   ├── config.py               its own settings
│   ├── email_auth/
│   ├── phone_auth/             ★ OTP — the primary patient path
│   ├── oauth_providers/
│   ├── session/
│   └── tests/
│
├── 02-questionnaire/       ← everything the questionnaire needs
│   ├── README.md · api.py · schemas.py · models.py · service.py · config.py
│   ├── speech_module/          ★ SUB-MODULE A — SPEAK
│   ├── type_module/            ★ SUB-MODULE B — TYPE
│   ├── question_engine/
│   │   └── flows/                  chest_pain · fever · cough · abdominal · headache
│   ├── report_check/           ★ the two closing questions
│   └── tests/
│
├── 03-document-ocr/        ← everything OCR needs
│   ├── README.md · OCR_MODULE.md · api.py · schemas.py · models.py · service.py · config.py
│   ├── upload/ · classifier/
│   ├── handwritten_prescription/   ★ TrOCR + formulary constraint
│   ├── lab_report/                 ★ PaddleOCR table-aware
│   ├── imaging_reports/            sonography · CT · MRI · X-ray · ECG
│   ├── extraction/
│   └── tests/corpus/
│
├── 04-summary-engine/      ← everything the summary needs
│   ├── README.md · api.py · schemas.py · models.py · service.py · config.py
│   ├── aggregator/ · generator/
│   ├── safety/                 ★ blocks diagnostic language, fails closed
│   ├── red_flag/
│   └── tests/
│
├── 05-doctor-portal/       ← everything the doctor screen needs
│   ├── README.md · api.py · schemas.py · models.py · service.py · config.py
│   ├── queue/
│   ├── patient_info/           ① · summary_view/ ② · questionnaire_view/ ③ · reports_view/ ④
│   └── tests/
│
└── 06-platform/            ← the ONLY shared module — everyone stands on it
    ├── README.md
    ├── app.py                  ★ the FastAPI app — mounts every module's router
    ├── api.py                  /health · /ready
    ├── schemas.py              error envelope + shared enums
    ├── config.py · service.py
    ├── database/               schema · repositories · migrations · seed
    ├── storage/                audio · documents · originals · crops
    ├── jobs/ · jobs_runtime/   background work for modules 03 and 04
    ├── runtime/                cache · queue · realtime · security · logging · audit · deps
    ├── http/
    │   ├── middleware/             auth · request_id · errors · ratelimit
    │   ├── ws/                     hub · doctor channel
    │   └── mocks.py
    └── tests/
```

**No shared `api/`, `core/`, `workers/` or `contracts/` folder.** If a module needs it, it is
in that module's folder. The only exception is `06-platform`, which is infrastructure every
module genuinely shares.

---

## The one import rule

```
✅  import 01-authentication.schemas       another module's PUBLIC schemas
✅  from platform_runtime import storage   the shared runtime in 06-platform
❌  import 01-authentication.service       another module's internals
❌  import 01-authentication.models        another module's tables
```

**`schemas.py` is the contract. Everything else in a module folder is private.**

If you find yourself importing another module's `service.py`, stop — put the shape in that
module's `schemas.py` instead, and tell the team.

---

## ⚠ One constraint you must know about

**A folder named `01-authentication` is not a valid Python package name.** Python identifiers
cannot start with a digit or contain a hyphen, so this fails:

```python
import 01-authentication.api        # SyntaxError
```

This does **not** mean the folder names are wrong — it means modules are loaded **by path**,
not by import statement. `06-platform/app.py` discovers and mounts them:

```python
# 06-platform/app.py
import importlib.util, pathlib
from fastapi import FastAPI

BACKEND = pathlib.Path(__file__).resolve().parent.parent
app = FastAPI(title="MediKiosk API")


def load(folder: str, filename: str = "api.py"):
    """Load a module by PATH, because the folder name is not an identifier."""
    path = BACKEND / folder / filename
    spec = importlib.util.spec_from_file_location(
        folder.replace("-", "_"), path)          # 01-authentication -> 01_authentication
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


for folder in sorted(p.name for p in BACKEND.iterdir()
                     if p.is_dir() and p.name[0].isdigit()):
    app.include_router(load(folder).router, prefix="/api")
```

Two consequences to plan for:

| | |
|---|---|
| **Mounting is automatic** | drop a new numbered folder in and it is picked up — no registration list to edit |
| **Cross-module imports need the same loader** | when 04 needs 02's schemas, use `load("02-questionnaire", "schemas.py")`, or add a small `sys.path` shim in `06-platform/runtime/deps.py` |

If the team would rather use plain `import` statements, rename the folders to
`m01_authentication`, `m02_questionnaire`, … — valid identifiers that keep the visible ordering.
**Decide this on day 1, before anyone writes an import.**

---

## The pipeline — and where each module hands over

```
 01-authentication          who is this
        │  session { user_id, role }
        ▼
 02-questionnaire           SPEAK | TYPE → answers → ⚠ red-flag rules
        │                                       │
        │        "Do you have reports / prescriptions?"
        │                       │               │
        │              ┌────────┴────────┐      │ red flag fires
        │             YES                NO     │ → jumps STRAIGHT to 05
        │              │                 │      │    (does not wait for 03/04)
        │              ▼                 │      │
 03-document-ocr   prescriptions · lab   │      │
                   sonography · CT · MRI │      │
                   X-ray · ECG           │      │
                       │                 │      │
                       └────────┬────────┘      │
                                ▼               │
 04-summary-engine     aggregate → summarise    │
                       → source check           │
                       → 🛡 safety check         │
                                ▼               │
 05-doctor-portal      ① info ② summary ────────┘
                       ③ questionnaire ④ reports
                                │
                       doctor edits ──► writes corrections BACK to 03 and 04
                                ▼
                       confirmed · stored · visible to the patient

 06-platform           database · storage · jobs · runtime   (underneath all of it)
```

**Each module's README has a `🔌 CONNECTIONS` section** stating exactly who calls it, what it
calls next, under what condition, and the JSON it hands over.

---

## Conditional calls — the two that matter

| From | To | Condition |
|---|---|---|
| 02 → 03 | document OCR | **only if** the patient answered yes to reports or prescriptions |
| 02 → 05 | doctor portal | **only if** a red flag fires — immediately, skipping 03 and 04 |
| 02 → 04 | summary engine | **always**, even for a partial or abandoned questionnaire |
| 05 → 03/04 | corrections | **only** when a doctor edits or verifies something |

Everything else in the chain is unconditional.

---

## Six rules every module obeys

1. **Never diagnose.** No disease name, no treatment, no drug recommendation — anywhere.
2. **Never state a fact without saying where it came from.**
3. **Never merge conflicting information.** Show both; the doctor decides.
4. **Never block the patient.** Any question is skippable; a partial record is still valuable.
5. **Degrade, never crash.** The patient must never see a stack trace.
6. **The doctor makes the clinical decision.** We collect, structure and present.

---

## Run

```bash
cp ../.env.example .env

# everything, in Docker
docker compose up --build

# or manually — the app lives in 06-platform
uvicorn 06-platform.app:app --reload --host 0.0.0.0 --port 8000
```

> If the folder-name constraint above bites, run it as
> `uvicorn --app-dir 06-platform app:app` instead.

**Background worker** (module 03 OCR jobs, module 04 summary jobs):

```bash
celery -A 06-platform.jobs_runtime.celery_app worker -l info -Q ocr --concurrency=2
```

**Work against fixtures while other modules are unfinished:**

```bash
MOCK=02,03,04 docker compose up
```

Drop a number once that module is real. This is how six people build in parallel without
waiting for each other. **06-platform ships the schema and the mocks on day 1**, or everyone
else is blocked.

---

## Migrations and seed data

```bash
alembic upgrade head
python 06-platform/database/seed.py --demo
```

---

## Reference

| | |
|---|---|
| Full architecture | `docs/ARCHITECTURE.md` |
| Every JSON shape | `docs/DATA_CONTRACTS.md` |
| Every endpoint | `docs/API_SPEC.md` |
| The OCR module in depth | `03-document-ocr/OCR_MODULE.md` |
| Your module's spec, and its connections | the `README.md` in that module's folder |

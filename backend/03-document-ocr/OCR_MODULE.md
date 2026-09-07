# OCR_MODULE.md
## Hybrid OCR Module — Patient/Doctor Medical Records Portal

**Module:** `03-document-ocr`
**Project:** MediKiosk (SIH26047 — Patient Case-Taking Software)
**Hybrid OCR:** **PaddleOCR 3.x** (printed text, tables, layout) **+ TrOCR** (handwriting)
**Frontend:** React 18 + Vite + TypeScript
**Backend:** Python 3.11 + FastAPI + Celery
**Database:** PostgreSQL 16 (+ Redis for the job queue, MinIO/S3 for files)
**Deployment:** Docker Compose (local dev) → single cloud VM

---

# Table of Contents

1. [Overview](#1-overview)
2. [Architecture](#2-architecture)
3. [Prerequisites & Installation](#3-prerequisites--installation)
4. [Backend Implementation Steps](#4-backend-implementation-steps)
5. [Frontend — Patient Portal](#5-frontend--patient-portal)
6. [Frontend — Doctor Portal](#6-frontend--doctor-portal)
7. [End-to-End Connectivity](#7-end-to-end-connectivity)
8. [Testing Steps](#8-testing-steps)
9. [Folder Structure Tree](#9-folder-structure-tree)
10. [Run Instructions](#10-run-instructions)

---

# 1. Overview

## 1.1 What this module does

A patient arrives at the hospital carrying a plastic bag of paper — old prescriptions, blood
reports, lab printouts. Today a doctor with two minutes has to read all of it manually.

This module turns that paper into structured, searchable, flagged clinical data **before** the
patient reaches the consultation room.

| Input | Output |
|---|---|
| Scanned images (JPG/PNG/WEBP) and PDFs uploaded by the patient | Structured clinical facts, dated and ordered |
| **Handwritten doctor prescriptions** | Medicine name, dose, frequency, duration — with a confidence score, or an honest refusal |
| **Printed lab / blood reports** | Test name, value, unit, reference range, ↑↓ abnormal flag |
| **Ultrasound / sonography reports** (image or PDF) | Modality, region, date, **quoted impression**, findings, attention terms |
| **X-ray reports** (image or PDF) | same as above |
| **CT and MRI reports** (usually multi-page PDF) | same, parsed across all pages as one document |
| **ECG reports** | Rate, PR, QRS, QT/QTc + the quoted interpretation line |
| Any document | A short summary paragraph + a bulleted list of what the doctor should not miss |

**Three parsing paths, because these are three genuinely different problems:**

```
LAB REPORT              PRESCRIPTION            IMAGING / SCAN REPORT
printed TABLE           HANDWRITING             printed NARRATIVE
     │                       │                          │
     ▼                       ▼                          ▼
PaddleOCR               TrOCR                     PaddleOCR
structure mode          + formulary               section splitter
     │                  constraint                     │
     ▼                       │                         ▼
test ↔ value ↔ unit          ▼                  IMPRESSION extracted
↔ reference range       drug · dose ·           quoted verbatim,
     │                  frequency · duration     attributed
     ▼                       │                         │
compare to range        confidence gate          attention terms
↑ ↓ flag                ABSTAIN if unsure        (keyword, not judgement)
```

> **The scan image itself is stored and shown to the doctor — never analysed.**
> We read the radiologist's report. Interpreting an X-ray from the image is a different,
> regulated problem and this module does not do it.

## 1.2 The one boundary that shapes everything

> **This module extracts and compares. It never diagnoses.**
>
> "Haemoglobin 8.2 g/dL — below the reference range 12–16" is a **fact**.
> "Patient has anaemia" is a **diagnosis** and this module must never produce it.
>
> Red-flag detection here means *"this number is outside the printed reference range"* — nothing more.
> The doctor draws the clinical conclusion.

## 1.3 End-to-end flow

```
┌──────────────────────────────────────────────────────────────────────┐
│                          PATIENT PORTAL                              │
└──────────────────────────────────────────────────────────────────────┘
                                  │
              1. PATIENT UPLOADS  │  drag-drop, camera, or file picker
                 JPG / PNG / PDF  │  multiple files at once
                                  ▼
                    ┌─────────────────────────┐
                    │  POST /api/uploads      │
                    │  validate type + size   │
                    │  store original in S3   │
                    │  create DB row          │
                    │  enqueue OCR job        │
                    │  RETURN 202 immediately │  ← patient never waits
                    └────────────┬────────────┘
                                 │
                                 ▼
┌──────────────────────────────────────────────────────────────────────┐
│                     BACKGROUND WORKER (Celery)                       │
└──────────────────────────────────────────────────────────────────────┘
                                 │
              2. PREPROCESSING   ▼
                    PDF → page images (300 DPI)
                    deskew · denoise · shadow removal · contrast (CLAHE)
                    KEEP THE ORIGINAL UNTOUCHED
                                 │
              3. CLASSIFY        ▼
                    lab_report | prescription | imaging_report | other
                                 │
              4. HYBRID OCR      ▼
                    ┌────────────┴────────────┐
                    │  REGION SEGMENTATION    │
                    │  which blocks are       │
                    │  printed vs handwritten │
                    └────┬───────────────┬────┘
                         │               │
                  PRINTED│               │HANDWRITTEN
                         ▼               ▼
                   PaddleOCR          TrOCR
                   • text + bbox      • line-level recognition
                   • table structure  • constrained to the
                   • confidence         Indian drug formulary
                         │               │
                         └───────┬───────┘
                                 ▼
                         MERGE + CONFIDENCE
                         (see §2.4)
                                 │
              5. PARSE           ▼
        ┌────────────────────────┼────────────────────────┐
        ▼                        ▼                        ▼
   LAB REPORT              PRESCRIPTION           IMAGING / SCAN
   table structure         handwriting            narrative sections
   test · value ·          medicine · dose ·      modality · region ·
   unit · ref range        frequency · duration   date · FINDINGS ·
                                                  ★ IMPRESSION · advice
                                                  (ECG: rate · PR · QRS)
        │                        │                        │
        ▼                        ▼                        ▼
   6. FLAGGING — three different mechanisms
        │                        │                        │
   value vs range          confidence gate         attention terms
   ↑ HIGH  ↓ LOW           ≥0.85 accept            keyword scan of the
   🚨 CRITICAL             <0.60 ABSTAIN           radiologist's own words
   (arithmetic)            (no guessing)           + negation detection
                                                   (ⓘ not 🚨 — we are not
                                                    making a judgement)
        └────────────────────────┼────────────────────────┘
                                 │
              7. SUMMARIZE       ▼
                    short paragraph (3–5 sentences)
                    + bulleted red-flag list
                    every line carries its SOURCE
                                 │
              8. PERSIST         ▼
                    extracted_report rows · summary row · flags
                    WebSocket push → doctor portal
                                 │
                                 ▼
┌──────────────────────────────────────────────────────────────────────┐
│                          DOCTOR PORTAL                               │
│                                                                      │
│   list of patient uploads  →  click one  →  summary paragraph        │
│                                            🔴 red-flag bullets       │
│                                            structured values table   │
│                                            [ view original scan ]    │
└──────────────────────────────────────────────────────────────────────┘
```

## 1.4 Latency budget

| Stage | Target |
|---|---|
| Upload accepted (API response) | **< 400 ms** — never blocks the patient |
| Preprocessing per page | ~300 ms |
| PaddleOCR per page | 1–3 s CPU |
| TrOCR per handwritten line | 200–400 ms CPU |
| Parse + flag + summarize | < 1 s |
| **Total per typical document** | **4–12 s**, in the background |

---

# 2. Architecture

## 2.1 Why a hybrid, and not one engine

| | PaddleOCR 3.x | TrOCR (`microsoft/trocr-*`) |
|---|---|---|
| Printed text | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| Tables / layout structure | ⭐⭐⭐⭐⭐ | ⭐ (none) |
| Handwriting | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| Multilingual / Indic scripts | ⭐⭐⭐⭐ | ⭐⭐ |
| Runs offline | ✅ | ✅ |
| Speed | Fast | Slower (transformer, per line) |
| Gives bounding boxes | ✅ | ❌ (needs a detector to feed it) |

**Neither engine alone is sufficient for our documents.**

- A blood report is a **printed table**. PaddleOCR's structure mode keeps
  `test ↔ value ↔ unit ↔ reference range` linked in one row. TrOCR would return a
  meaningless stream of disconnected words.
- A doctor's prescription is **handwriting**. PaddleOCR's recogniser is trained on printed
  glyphs and degrades badly. TrOCR was built for exactly this.
- A real prescription is **both** — printed letterhead and pre-printed field labels around
  handwritten drug lines.

**So we do not "pick one engine per document". We segment the page and route each region.**

## 2.2 Combination strategy: region-level routing + selective dual-run

We use **primary + specialist routing**, not naive parallel voting on the whole page.

```
                     PREPROCESSED PAGE
                            │
                            ▼
              ┌───────────────────────────┐
              │  PaddleOCR DETECTION      │   always runs first
              │  → text region boxes      │   it gives us the boxes
              └─────────────┬─────────────┘
                            ▼
              ┌───────────────────────────┐
              │  HANDWRITING CLASSIFIER   │   small CNN on each crop
              │  per region → P(handwritten)│
              └─────────────┬─────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                   ▼
   P < 0.35            0.35 ≤ P ≤ 0.65      P > 0.65
   PRINTED             UNCERTAIN            HANDWRITTEN
        │                   │                   │
        ▼                   ▼                   ▼
   PaddleOCR          RUN BOTH             TrOCR
   recognition        then choose          recognition
        │             by confidence            │
        │                   │                   │
        └───────────────────┴───────────────────┘
                            ▼
                      MERGED PAGE TEXT
                  every token: text · bbox
                  · confidence · engine
```

**Why not run both on everything?** TrOCR is ~10× slower per region. On a 60-region lab
report that turns a 3-second job into 30 seconds for zero accuracy gain — printed text is
where PaddleOCR is already strongest.

**The uncertain band (0.35–0.65) is where dual-run pays for itself** — it is typically 5–15%
of regions on a real prescription, so the cost is bounded.

## 2.3 Fallback chain

Every stage degrades instead of failing.

```
PaddleOCR detection fails
        ▼
  fall back to a simple contour/MSER text-region detector
        ▼
    still nothing?  → treat the WHOLE PAGE as one region
        ▼
TrOCR model unavailable (OOM / not downloaded)
        ▼
  run PaddleOCR on handwritten regions anyway,
  and cap the confidence at 0.45 so it lands in VERIFY
        ▼
Both engines return empty
        ▼
  emit a "could not read" record WITH the page image
  attached, so the doctor still sees the scan
```

> **Never return "nothing". Always return at least the image.** A doctor looking at the original
> scan is strictly better than a doctor seeing a blank screen.

## 2.4 Merge & confidence scoring

### Per-region confidence

```python
region_confidence = engine_confidence * layout_penalty * lexicon_bonus
```

| Term | Range | Meaning |
|---|---|---|
| `engine_confidence` | 0–1 | raw score from PaddleOCR or TrOCR |
| `layout_penalty` | 0.7–1.0 | 1.0 if the region is cleanly bounded; 0.7 if it overlaps another region or is clipped at the page edge |
| `lexicon_bonus` | 0.8–1.15 | 1.15 if the decoded text exactly matches a known drug/test name; 1.0 if it is a number or date; 0.8 if it matches nothing known |

### When both engines ran on the same region

```python
def choose(paddle_result, trocr_result, is_medicine_context: bool):
    p, t = paddle_result, trocr_result

    # exact agreement → highest confidence
    if normalize(p.text) == normalize(t.text):
        return p.text, min(0.99, max(p.conf, t.conf) + 0.10), "both"

    # in a medicine line, a formulary match wins outright
    if is_medicine_context:
        p_hit = formulary.exact_match(p.text)
        t_hit = formulary.exact_match(t.text)
        if t_hit and not p_hit:
            return t.text, t.conf, "trocr"
        if p_hit and not t_hit:
            return p.text, p.conf, "paddleocr"

    # otherwise the higher score wins, but disagreement costs confidence
    winner = p if p.conf >= t.conf else t
    penalty = 0.85 if levenshtein_ratio(p.text, t.text) < 0.6 else 0.95
    return winner.text, winner.conf * penalty, winner.engine
```

### Confidence bands → what happens

| Band | Action |
|---|---|
| **≥ 0.85** | Auto-accept. Structured into the report. |
| **0.60 – 0.85** | Accept, but mark `needs_verification = true`. Doctor sees a soft ⚠ marker. |
| **< 0.60** | **Abstain.** Emit **no value**. Store the cropped image. Doctor sees `⚠ could not read — [show the ink]`. |

> **The abstention rule is the most important design decision in this module.**
> A prescription that *might* say "Metformin 500 mg" must never silently become a confirmed
> medication. Knowing that it cannot read a line is a safer and stronger result than a
> confident wrong drug name.

## 2.5 Constrained decoding for handwritten medicines

A doctor writing a prescription is not writing arbitrary English. They are writing from a
**closed set**. We exploit that.

```
TrOCR raw output:  "Melformn 50 od"
                          │
                          ▼
        ┌─────────────────────────────────────┐
        │  LEXICON SNAP                       │
        │  fuzzy-match against formulary.txt  │
        │  (generic + brand + AYUSH, ~15k)    │
        │  phonetic + Levenshtein             │
        └─────────────────┬───────────────────┘
                          ▼
        best match: "Metformin"   distance 2   score 0.82
                          │
              ┌───────────┴───────────┐
        score ≥ 0.75              score < 0.75
              │                       │
              ▼                       ▼
        emit "Metformin"         ABSTAIN
        conf = 0.82              no value emitted
```

**The model is structurally incapable of emitting a drug that does not exist**, because
anything that fails to snap to the lexicon is discarded rather than guessed.

Three implementation levels — **build A first**:

| | Approach | Effort | Quality |
|---|---|---|---|
| **A** | Post-hoc lexicon snap (above) | Low | Good — **start here** |
| **B** | Generate n-best beams, re-rank by lexicon membership | Medium | Better |
| **C** | Trie-based logit masking during decoding | High | Best |

## 2.6 Image preprocessing pipeline

Order matters. Each step feeds the next.

```
 1. LOAD
    PDF → pdf2image at 300 DPI (200 DPI floor)
    HEIC/WEBP → PNG
    EXIF orientation applied

 2. DOWNSCALE GUARD
    longest side capped at 2400 px (memory + speed)

 3. DESKEW
    Hough transform on detected text baselines
    rotate to horizontal, ±15° range

 4. PERSPECTIVE CORRECTION
    detect the 4 document corners
    warp to a flat rectangle
    (only if all 4 corners are found with confidence)

 5. SHADOW / ILLUMINATION REMOVAL
    morphological background estimate, then divide it out
    fixes the classic "photo taken under a ceiling light" case

 6. DENOISE
    fastNlMeansDenoising — mild, do not smear thin handwriting

 7. CONTRAST
    CLAHE, clipLimit=2.0, tileGridSize=(8,8)

 8. BINARISE            ← handwriting path ONLY
    adaptive Gaussian threshold
    PaddleOCR receives the GREYSCALE image, not the binarised one

 9. STORE
    original.jpg     ← never overwritten, all crops come from this
    processed.jpg    ← what the engines see
    transform.json   ← the matrix, so bboxes can be mapped BACK
```

> ### ⚠ The bug that will bite you
>
> After deskew and perspective warp, a bounding box is in **processed-image coordinates**.
> If you crop the original using those coordinates, "show me the ink" shows the wrong region
> of the page. **Always invert the transform before cropping the original.** Write a test for
> this explicitly — it is the single most common defect in a pipeline of this shape.

---

# 3. Prerequisites & Installation

> All commands are shown for Linux/macOS and Windows (PowerShell). Docker instructions are at
> the end of this section and are the recommended path.

## 3.1 System requirements

| | Minimum | Recommended |
|---|---|---|
| CPU | 4 cores | 8 cores |
| RAM | 8 GB | 16 GB |
| Disk | 15 GB free (models ~4 GB) | 30 GB |
| GPU | not required | NVIDIA 6 GB+ (≈5× faster) |
| Python | 3.11 | 3.11 |
| Node.js | 18 | 20 LTS |

## 3.2 Step 1 — Install system dependencies

These are OS packages the Python libraries link against.

**Ubuntu / Debian**

```bash
sudo apt-get update
sudo apt-get install -y \
  python3.11 python3.11-venv python3.11-dev \
  build-essential \
  poppler-utils \
  libgl1 libglib2.0-0 \
  libsm6 libxext6 libxrender-dev \
  postgresql-client \
  git curl
```

**macOS (Homebrew)**

```bash
brew install python@3.11 poppler postgresql@16 node git
```

**Windows (PowerShell as Administrator)**

```powershell
winget install Python.Python.3.11
winget install OpenJS.NodeJS.LTS
winget install PostgreSQL.PostgreSQL.16
winget install Git.Git

# Poppler — required for PDF → image
# Download from https://github.com/oschwartz10612/poppler-windows/releases
# Extract to C:\poppler, then add C:\poppler\Library\bin to PATH:
$env:Path += ";C:\poppler\Library\bin"
[Environment]::SetEnvironmentVariable("Path", $env:Path, "User")
```

**Verify poppler is on PATH** (PDF support fails silently without it):

```bash
pdftoppm -v
```

## 3.3 Step 2 — Create the Python environment

```bash
cd backend
python3.11 -m venv .venv

# Linux / macOS
source .venv/bin/activate

# Windows PowerShell
.\.venv\Scripts\Activate.ps1

python -m pip install --upgrade pip setuptools wheel
```

## 3.4 Step 3 — Install OCR Engine 1: PaddleOCR

PaddlePaddle must be installed **before** PaddleOCR, and the CPU/GPU build differs.

**CPU build (default — use this unless you have a CUDA GPU)**

```bash
pip install paddlepaddle==3.0.0
pip install paddleocr==3.0.0
```

**GPU build (CUDA 11.8)**

```bash
pip install paddlepaddle-gpu==3.0.0
pip install paddleocr==3.0.0
```

**Download the models once** (first run downloads ~200 MB; do it now, not during a demo):

```bash
python - <<'PY'
from paddleocr import PaddleOCR
# lang="en" covers Latin script; add a second instance for Devanagari if needed
ocr = PaddleOCR(use_angle_cls=True, lang="en", show_log=False)
print("PaddleOCR models downloaded and ready")
PY
```

Models cache to `~/.paddleocr/` (Linux/macOS) or `C:\Users\<you>\.paddleocr\` (Windows).

## 3.5 Step 4 — Install OCR Engine 2: TrOCR

TrOCR runs on HuggingFace Transformers + PyTorch.

**CPU**

```bash
pip install torch==2.3.0 torchvision==0.18.0 --index-url https://download.pytorch.org/whl/cpu
pip install transformers==4.41.0 sentencepiece==0.2.0
```

**GPU (CUDA 11.8)**

```bash
pip install torch==2.3.0 torchvision==0.18.0 --index-url https://download.pytorch.org/whl/cu118
pip install transformers==4.41.0 sentencepiece==0.2.0
```

**Pre-download the handwriting model** (~1.4 GB):

```bash
python - <<'PY'
from transformers import TrOCRProcessor, VisionEncoderDecoderModel
name = "microsoft/trocr-base-handwritten"
TrOCRProcessor.from_pretrained(name)
VisionEncoderDecoderModel.from_pretrained(name)
print("TrOCR downloaded and ready")
PY
```

| Model | Size | Use |
|---|---|---|
| `microsoft/trocr-small-handwritten` | ~300 MB | fast, lower accuracy — good for a laptop demo |
| `microsoft/trocr-base-handwritten` | ~1.4 GB | **recommended default** |
| `microsoft/trocr-large-handwritten` | ~4 GB | best, needs GPU |

## 3.6 Step 5 — Install image and PDF processing

```bash
pip install \
  opencv-python-headless==4.10.0.84 \
  pillow==10.3.0 \
  pdf2image==1.17.0 \
  numpy==1.26.4 \
  scikit-image==0.23.2 \
  python-Levenshtein==0.25.1 \
  rapidfuzz==3.9.0
```

## 3.7 Step 6 — Install the backend framework

```bash
pip install \
  fastapi==0.111.0 \
  "uvicorn[standard]==0.30.1" \
  python-multipart==0.0.9 \
  pydantic==2.7.1 \
  pydantic-settings==2.3.0 \
  sqlalchemy==2.0.30 \
  alembic==1.13.1 \
  "psycopg[binary]==3.1.19" \
  celery==5.4.0 \
  redis==5.0.4 \
  boto3==1.34.120 \
  python-jose[cryptography]==3.3.0 \
  passlib[bcrypt]==1.7.4
```

Freeze it:

```bash
pip freeze > requirements.txt
```

## 3.8 Step 7 — Database setup

**Create the database and user**

```bash
# Linux / macOS
sudo -u postgres psql
```

```sql
CREATE DATABASE medikiosk;
CREATE USER medikiosk WITH ENCRYPTED PASSWORD 'change_me';
GRANT ALL PRIVILEGES ON DATABASE medikiosk TO medikiosk;
\c medikiosk
GRANT ALL ON SCHEMA public TO medikiosk;
\q
```

**Verify the connection**

```bash
psql "postgresql://medikiosk:change_me@localhost:5432/medikiosk" -c "SELECT version();"
```

**Run the migrations** (after §4.7 defines them)

```bash
cd backend
alembic upgrade head
```

## 3.9 Step 8 — Redis (job queue) and MinIO (file storage)

Easiest via Docker, even in local dev:

```bash
docker run -d --name mk-redis -p 6379:6379 redis:7-alpine

docker run -d --name mk-minio \
  -p 9000:9000 -p 9001:9001 \
  -e MINIO_ROOT_USER=medikiosk \
  -e MINIO_ROOT_PASSWORD=change_me_12345 \
  -v mk-minio-data:/data \
  minio/minio:latest server /data --console-address ":9001"
```

Create the buckets (console at http://localhost:9001, or via CLI):

```bash
docker run --rm --network host minio/mc:latest sh -c "
  mc alias set local http://localhost:9000 medikiosk change_me_12345 &&
  mc mb -p local/mk-originals &&
  mc mb -p local/mk-processed &&
  mc mb -p local/mk-crops
"
```

## 3.10 Step 9 — Install the frontend

```bash
cd frontend

# Patient app
npm create vite@latest patient_app -- --template react-ts
cd patient_app
npm install
npm install axios react-router-dom react-dropzone
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p
cd ..

# Doctor portal
npm create vite@latest doctor_portal -- --template react-ts
cd doctor_portal
npm install
npm install axios react-router-dom
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p
cd ..
```

## 3.11 Step 10 — Environment variables

Create `backend/.env`:

```bash
# ---------- database ----------
DATABASE_URL=postgresql+psycopg://medikiosk:change_me@localhost:5432/medikiosk

# ---------- queue ----------
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2

# ---------- file storage ----------
S3_ENDPOINT=http://localhost:9000
S3_ACCESS_KEY=medikiosk
S3_SECRET_KEY=change_me_12345
S3_BUCKET_ORIGINALS=mk-originals
S3_BUCKET_PROCESSED=mk-processed
S3_BUCKET_CROPS=mk-crops
S3_REGION=us-east-1

# ---------- OCR engines ----------
# Both engines run LOCALLY. No cloud API key is required for the default setup.
PADDLE_LANG=en
PADDLE_USE_GPU=false
PADDLE_USE_ANGLE_CLS=true

TROCR_MODEL=microsoft/trocr-base-handwritten
TROCR_DEVICE=cpu                    # cpu | cuda
TROCR_MAX_LINES_PER_PAGE=80         # safety cap

HANDWRITING_CLASSIFIER_PATH=models/handwriting_cls.onnx

# ---------- confidence thresholds ----------
CONF_AUTO_ACCEPT=0.85
CONF_VERIFY_FLOOR=0.60
LEXICON_SNAP_THRESHOLD=0.75
HANDWRITING_P_PRINTED=0.35
HANDWRITING_P_HANDWRITTEN=0.65

# ---------- preprocessing ----------
PDF_DPI=300
MAX_IMAGE_LONG_SIDE=2400
MAX_UPLOAD_MB=25
ALLOWED_MIME=image/jpeg,image/png,image/webp,application/pdf

# ---------- auth ----------
JWT_SECRET=change_me_to_a_long_random_string
ACCESS_TOKEN_MINUTES=30

# ---------- optional cloud fallback (DISABLED by default) ----------
# Turning this on sends patient documents off-premises.
# It requires an explicit clinic setting AND patient consent.
CLOUD_OCR_ENABLED=false
CLOUD_OCR_PROVIDER=
CLOUD_OCR_API_KEY=
```

Create `frontend/patient_app/.env` and `frontend/doctor_portal/.env`:

```bash
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000/ws
```

## 3.12 Recommended path — Docker Compose

Skips every step above except the `.env` file.

```yaml
# docker-compose.yml
services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: medikiosk
      POSTGRES_USER: medikiosk
      POSTGRES_PASSWORD: change_me
    volumes: [pg:/var/lib/postgresql/data]
    ports: ["5432:5432"]
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U medikiosk"]
      interval: 5s
      retries: 10

  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]

  minio:
    image: minio/minio:latest
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: medikiosk
      MINIO_ROOT_PASSWORD: change_me_12345
    volumes: [minio:/data]
    ports: ["9000:9000", "9001:9001"]

  backend:
    build: ./backend
    env_file: ./backend/.env
    depends_on:
      postgres: { condition: service_healthy }
      redis:    { condition: service_started }
      minio:    { condition: service_started }
    volumes:
      - ./backend:/app
      - models:/root/.cache          # persist downloaded OCR models
      - paddle:/root/.paddleocr
    ports: ["8000:8000"]
    command: uvicorn main:app --host 0.0.0.0 --port 8000 --reload

  worker:
    build: ./backend
    env_file: ./backend/.env
    depends_on: [backend, redis]
    volumes:
      - ./backend:/app
      - models:/root/.cache
      - paddle:/root/.paddleocr
    command: celery -A workers.celery_app worker -l info -Q ocr --concurrency=2

  patient_app:
    build: ./frontend/patient_app
    ports: ["3000:3000"]
    depends_on: [backend]

  doctor_portal:
    build: ./frontend/doctor_portal
    ports: ["3001:3000"]
    depends_on: [backend]

volumes:
  pg:
  minio:
  models:
  paddle:
```

`backend/Dockerfile`:

```dockerfile
FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
      poppler-utils libgl1 libglib2.0-0 libsm6 libxext6 libxrender-dev \
      build-essential curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Bake the models into the image so the first request is not a 2-minute download
RUN python -c "from paddleocr import PaddleOCR; PaddleOCR(lang='en', show_log=False)" && \
    python -c "from transformers import TrOCRProcessor, VisionEncoderDecoderModel; \
               n='microsoft/trocr-base-handwritten'; \
               TrOCRProcessor.from_pretrained(n); VisionEncoderDecoderModel.from_pretrained(n)"

COPY . .
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Bring it all up:

```bash
docker compose up --build
```

---

# 4. Backend Implementation Steps

## 4.1 Module folder structure

```
backend/03-document-ocr/
├── OCR_MODULE.md                 ← this document
├── __init__.py
│
├── api/
│   ├── __init__.py
│   ├── routes.py                 upload · status · list · summary · original
│   └── schemas.py                Pydantic request/response models
│
├── upload/
│   ├── __init__.py
│   ├── validate.py               MIME sniffing, size, page count
│   ├── store.py                  S3/MinIO put + presigned URLs
│   └── enqueue.py                push the Celery job
│
├── preprocessing/
│   ├── __init__.py
│   ├── pdf.py                    pdf2image at configured DPI
│   ├── pipeline.py               the ordered 9-step chain
│   ├── deskew.py
│   ├── perspective.py
│   ├── shadow.py
│   └── transform.py              ★ invert the matrix to map bboxes back
│
├── classifier/
│   ├── __init__.py
│   ├── document_type.py          lab | prescription | imaging | other
│   └── handwriting.py            per-region P(handwritten)
│
├── engines/
│   ├── __init__.py
│   ├── base.py                   OCRProvider interface — ALL engines implement this
│   ├── paddle_engine.py          PaddleOCR adapter
│   ├── trocr_engine.py           TrOCR adapter
│   ├── cloud_engine.py           optional, disabled by default
│   ├── router.py                 region → engine routing
│   └── merge.py                  ★ confidence scoring + dual-run resolution
│
├── lexicon/
│   ├── __init__.py
│   ├── formulary.txt             ~15k Indian drug names (generic + brand + AYUSH)
│   ├── lab_tests.txt             ~800 test names + synonyms
│   ├── snap.py                   fuzzy match + phonetic
│   └── notation.py               1-0-1 → BD · x5d · Tab. · SOS · OD/BD/TDS/HS
│
├── parsing/
│   ├── __init__.py
│   ├── lab_report.py             table → test/value/unit/range rows
│   ├── prescription.py           medicine/dose/frequency/duration
│   ├── imaging_report.py         modality · date · IMPRESSION section
│   └── dates.py                  date resolution — never invent one
│
├── flags/
│   ├── __init__.py
│   ├── reference_ranges.csv      fallback ranges by test, sex, age band
│   ├── critical.csv              panic values
│   ├── detect.py                 ★ value vs range → HIGH / LOW / CRITICAL
│   └── trends.py                 same test across dates → direction
│
├── summary/
│   ├── __init__.py
│   ├── generate.py               paragraph + bullets
│   ├── templates.py              deterministic fallback when the LLM is down
│   └── safety.py                 ★ blocks any diagnostic phrasing
│
├── tasks.py                      the Celery task — orchestrates the whole pipeline
├── models.py                     SQLAlchemy tables
├── repository.py                 all DB access for this module
│
└── tests/
    ├── test_preprocessing.py
    ├── test_bbox_roundtrip.py    ★ the crop-from-original test
    ├── test_merge.py
    ├── test_flags.py
    ├── test_notation.py
    └── corpus/                   100–300 labelled real documents
```

## 4.2 Step 1 — The upload endpoint

**Requirements**

- Accept `image/jpeg`, `image/png`, `image/webp`, `application/pdf`
- Max 25 MB per file, max 20 pages per PDF
- Validate by **magic bytes**, not by the filename extension
- Store the original untouched
- Return **immediately** with a job id — never wait for OCR

`api/routes.py`:

```python
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, status
from uuid import uuid4
from .schemas import UploadResponse
from ..upload import validate, store, enqueue
from ..repository import create_upload_row
from core.auth import current_patient

router = APIRouter(prefix="/api/uploads", tags=["documents"])


@router.post("", response_model=UploadResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_document(
    file: UploadFile = File(...),
    patient=Depends(current_patient),
):
    raw = await file.read()

    # 1. validate — magic bytes, size, page count
    v = validate.check(raw, file.filename, file.content_type)
    if not v.ok:
        raise HTTPException(422, detail={"code": v.code, "message": v.message})

    upload_id = uuid4()

    # 2. store the ORIGINAL, untouched
    key = f"{patient.id}/{upload_id}/original{v.extension}"
    store.put_original(key, raw, v.mime)

    # 3. create the DB row
    row = create_upload_row(
        upload_id=upload_id,
        patient_id=patient.id,
        filename=file.filename,
        mime=v.mime,
        size_bytes=len(raw),
        page_count=v.page_count,
        storage_key=key,
        status="QUEUED",
    )

    # 4. enqueue and return AT ONCE
    job_id = enqueue.ocr_job(upload_id=upload_id, patient_id=patient.id)

    return UploadResponse(
        upload_id=upload_id,
        job_id=job_id,
        status="QUEUED",
        filename=file.filename,
        page_count=v.page_count,
        poll_url=f"/api/uploads/{upload_id}",
    )
```

`upload/validate.py` — magic-byte checking:

```python
import io
from dataclasses import dataclass
from pypdf import PdfReader
from PIL import Image

MAGIC = {
    b"\xff\xd8\xff":            ("image/jpeg", ".jpg"),
    b"\x89PNG\r\n\x1a\n":       ("image/png",  ".png"),
    b"RIFF":                    ("image/webp", ".webp"),   # + "WEBP" at offset 8
    b"%PDF-":                   ("application/pdf", ".pdf"),
}

@dataclass
class Result:
    ok: bool
    mime: str = ""
    extension: str = ""
    page_count: int = 1
    code: str = ""
    message: str = ""


def check(raw: bytes, filename: str, declared_mime: str,
          max_mb: int = 25, max_pages: int = 20) -> Result:

    if len(raw) > max_mb * 1024 * 1024:
        return Result(False, code="FILE_TOO_LARGE",
                      message=f"File is larger than {max_mb} MB.")

    mime = ext = None
    for sig, (m, e) in MAGIC.items():
        if raw.startswith(sig):
            mime, ext = m, e
            break
    if mime is None:
        return Result(False, code="UNSUPPORTED_TYPE",
                      message="Only JPG, PNG, WEBP and PDF files are accepted.")

    if mime == "application/pdf":
        try:
            pages = len(PdfReader(io.BytesIO(raw)).pages)
        except Exception:
            return Result(False, code="CORRUPT_PDF",
                          message="This PDF could not be opened.")
        if pages > max_pages:
            return Result(False, code="TOO_MANY_PAGES",
                          message=f"PDFs are limited to {max_pages} pages.")
        return Result(True, mime, ext, page_count=pages)

    try:
        Image.open(io.BytesIO(raw)).verify()
    except Exception:
        return Result(False, code="CORRUPT_IMAGE",
                      message="This image file could not be opened.")

    return Result(True, mime, ext, page_count=1)
```

## 4.3 Step 2 — The OCR provider interface

**Build the abstraction on day one.** Nothing outside `engines/` may import PaddleOCR or
TrOCR directly. This is what lets us swap, benchmark, and fall back.

`engines/base.py`:

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Literal
import numpy as np


@dataclass
class Token:
    text: str
    bbox: tuple[int, int, int, int]        # x, y, w, h — PROCESSED image space
    confidence: float
    engine: Literal["paddleocr", "trocr", "both", "cloud"]


@dataclass
class Region:
    bbox: tuple[int, int, int, int]
    tokens: list[Token] = field(default_factory=list)
    is_handwritten_p: float = 0.0
    text: str = ""
    confidence: float = 0.0
    engine: str = ""


@dataclass
class PageResult:
    page_no: int
    regions: list[Region]
    tables: list[dict] = field(default_factory=list)   # PaddleOCR structure output
    width: int = 0
    height: int = 0


class OCRProvider(ABC):
    name: str

    @abstractmethod
    def detect(self, image: np.ndarray) -> list[tuple[int, int, int, int]]:
        """Return text region bounding boxes. May be unsupported."""

    @abstractmethod
    def recognize(self, image: np.ndarray,
                  boxes: list[tuple[int, int, int, int]] | None = None) -> PageResult:
        """Recognise text. If boxes is None, run full detection + recognition."""

    @abstractmethod
    def is_available(self) -> bool:
        """False if the model failed to load — the router will skip this engine."""
```

## 4.4 Step 3 — PaddleOCR adapter

`engines/paddle_engine.py`:

```python
import numpy as np
from paddleocr import PaddleOCR
from .base import OCRProvider, PageResult, Region, Token
from core.config import settings


class PaddleEngine(OCRProvider):
    name = "paddleocr"

    def __init__(self):
        self._ocr = None
        self._structure = None

    def _lazy(self):
        if self._ocr is None:
            self._ocr = PaddleOCR(
                lang=settings.PADDLE_LANG,
                use_angle_cls=settings.PADDLE_USE_ANGLE_CLS,
                use_gpu=settings.PADDLE_USE_GPU,
                show_log=False,
            )
        return self._ocr

    def is_available(self) -> bool:
        try:
            self._lazy()
            return True
        except Exception:
            return False

    def detect(self, image: np.ndarray):
        result = self._lazy().ocr(image, det=True, rec=False, cls=False)
        boxes = []
        for line in (result[0] or []):
            xs = [int(p[0]) for p in line]
            ys = [int(p[1]) for p in line]
            boxes.append((min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys)))
        return boxes

    def recognize(self, image: np.ndarray, boxes=None) -> PageResult:
        h, w = image.shape[:2]
        regions: list[Region] = []

        if boxes is None:
            result = self._lazy().ocr(image, cls=True)
            for line in (result[0] or []):
                poly, (text, conf) = line
                xs = [int(p[0]) for p in poly]
                ys = [int(p[1]) for p in poly]
                bbox = (min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys))
                regions.append(Region(
                    bbox=bbox, text=text, confidence=float(conf), engine=self.name,
                    tokens=[Token(text, bbox, float(conf), "paddleocr")],
                ))
        else:
            for bbox in boxes:
                x, y, bw, bh = bbox
                crop = image[y:y + bh, x:x + bw]
                if crop.size == 0:
                    continue
                res = self._lazy().ocr(crop, det=False, cls=True)
                if not res or not res[0]:
                    continue
                text, conf = res[0][0]
                regions.append(Region(
                    bbox=bbox, text=text, confidence=float(conf), engine=self.name,
                    tokens=[Token(text, bbox, float(conf), "paddleocr")],
                ))

        return PageResult(page_no=0, regions=regions, width=w, height=h)

    def extract_tables(self, image: np.ndarray) -> list[dict]:
        """
        PaddleOCR structure mode — CRITICAL for lab reports.
        Keeps test <-> value <-> unit <-> reference range linked in one row.
        """
        from paddleocr import PPStructure
        if self._structure is None:
            self._structure = PPStructure(show_log=False, layout=True, table=True)
        out = self._structure(image)
        return [b for b in out if b.get("type") == "table"]
```

## 4.5 Step 4 — TrOCR adapter with lexicon constraint

`engines/trocr_engine.py`:

```python
import numpy as np
import torch
from PIL import Image
from transformers import TrOCRProcessor, VisionEncoderDecoderModel
from .base import OCRProvider, PageResult, Region, Token
from ..lexicon.snap import snap_to_formulary
from core.config import settings


class TrOCREngine(OCRProvider):
    name = "trocr"

    def __init__(self):
        self._proc = None
        self._model = None
        self._device = settings.TROCR_DEVICE

    def _lazy(self):
        if self._model is None:
            self._proc = TrOCRProcessor.from_pretrained(settings.TROCR_MODEL)
            self._model = VisionEncoderDecoderModel.from_pretrained(settings.TROCR_MODEL)
            self._model.to(self._device).eval()
        return self._proc, self._model

    def is_available(self) -> bool:
        try:
            self._lazy()
            return True
        except Exception:
            return False

    def detect(self, image: np.ndarray):
        raise NotImplementedError("TrOCR has no detector — PaddleOCR supplies the boxes.")

    def recognize(self, image: np.ndarray, boxes=None,
                  medicine_context: bool = False) -> PageResult:
        if boxes is None:
            raise ValueError("TrOCR requires boxes from the detector.")

        proc, model = self._lazy()
        h, w = image.shape[:2]
        regions: list[Region] = []

        # hard cap — TrOCR is slow, do not let one bad page stall the queue
        boxes = boxes[: settings.TROCR_MAX_LINES_PER_PAGE]

        for bbox in boxes:
            x, y, bw, bh = bbox
            crop = image[y:y + bh, x:x + bw]
            if crop.size == 0 or bh < 8:
                continue

            pil = Image.fromarray(crop).convert("RGB")
            pixel_values = proc(images=pil, return_tensors="pt").pixel_values.to(self._device)

            with torch.no_grad():
                out = model.generate(
                    pixel_values,
                    max_new_tokens=48,
                    num_beams=4,
                    output_scores=True,
                    return_dict_in_generate=True,
                )

            text = proc.batch_decode(out.sequences, skip_special_tokens=True)[0].strip()
            conf = float(torch.exp(out.sequences_scores[0])) if hasattr(out, "sequences_scores") else 0.5

            # ★ constrained decoding, approach A — snap to the real formulary
            if medicine_context:
                snapped, score = snap_to_formulary(text)
                if snapped is None:
                    # no match within threshold → ABSTAIN, emit no value
                    regions.append(Region(bbox=bbox, text="", confidence=0.0,
                                          engine=self.name, is_handwritten_p=1.0))
                    continue
                text, conf = snapped, min(conf, score)

            regions.append(Region(
                bbox=bbox, text=text, confidence=conf, engine=self.name,
                is_handwritten_p=1.0,
                tokens=[Token(text, bbox, conf, "trocr")],
            ))

        return PageResult(page_no=0, regions=regions, width=w, height=h)
```

`lexicon/snap.py`:

```python
from functools import lru_cache
from pathlib import Path
from rapidfuzz import process, fuzz
from core.config import settings

LEX = Path(__file__).parent / "formulary.txt"


@lru_cache(maxsize=1)
def _formulary() -> list[str]:
    return [ln.strip() for ln in LEX.read_text(encoding="utf-8").splitlines() if ln.strip()]


def snap_to_formulary(text: str) -> tuple[str | None, float]:
    """
    Fuzzy-match OCR output to a REAL medicine name.
    Returns (None, 0.0) when nothing is close enough — the caller must then ABSTAIN.
    """
    if not text:
        return None, 0.0

    candidate = text.split()[0]          # the drug name is the first token
    match = process.extractOne(
        candidate, _formulary(),
        scorer=fuzz.WRatio,
        score_cutoff=settings.LEXICON_SNAP_THRESHOLD * 100,
    )
    if match is None:
        return None, 0.0
    name, score, _ = match
    return name, score / 100.0
```

## 4.6 Step 5 — The merge layer

`engines/merge.py`:

```python
from rapidfuzz import fuzz
from .base import Region
from core.config import settings


def _norm(s: str) -> str:
    return "".join(ch.lower() for ch in s if ch.isalnum())


def score_region(region: Region, overlaps: bool, lexicon_hit: bool | None) -> float:
    layout_penalty = 0.7 if overlaps else 1.0
    if lexicon_hit is True:
        lexicon_bonus = 1.15
    elif lexicon_hit is None:
        lexicon_bonus = 1.0          # a number or a date — nothing to look up
    else:
        lexicon_bonus = 0.8
    return min(1.0, region.confidence * layout_penalty * lexicon_bonus)


def resolve(paddle: Region | None, trocr: Region | None,
            medicine_context: bool = False) -> Region:
    """Both engines ran on the same region. Decide what the region says."""
    if paddle is None:
        return trocr
    if trocr is None:
        return paddle

    if _norm(paddle.text) == _norm(trocr.text):
        merged = paddle
        merged.confidence = min(0.99, max(paddle.confidence, trocr.confidence) + 0.10)
        merged.engine = "both"
        return merged

    if medicine_context:
        from ..lexicon.snap import snap_to_formulary
        _, p_score = snap_to_formulary(paddle.text)
        _, t_score = snap_to_formulary(trocr.text)
        if t_score >= settings.LEXICON_SNAP_THRESHOLD > p_score:
            return trocr
        if p_score >= settings.LEXICON_SNAP_THRESHOLD > t_score:
            return paddle

    winner = paddle if paddle.confidence >= trocr.confidence else trocr
    similarity = fuzz.ratio(paddle.text, trocr.text) / 100.0
    winner.confidence *= 0.85 if similarity < 0.6 else 0.95
    return winner


def band(confidence: float) -> str:
    if confidence >= settings.CONF_AUTO_ACCEPT:
        return "AUTO"
    if confidence >= settings.CONF_VERIFY_FLOOR:
        return "VERIFY"
    return "ABSTAIN"
```

`engines/router.py`:

```python
from .base import PageResult, Region
from .paddle_engine import PaddleEngine
from .trocr_engine import TrOCREngine
from .merge import resolve, band
from ..classifier.handwriting import p_handwritten
from core.config import settings

paddle = PaddleEngine()
trocr = TrOCREngine()


def run_page(image, doc_type: str, page_no: int) -> PageResult:
    # 1. PaddleOCR always detects — it supplies the boxes for both engines
    boxes = paddle.detect(image) if paddle.is_available() else _fallback_detect(image)

    # 2. classify each region
    printed, uncertain, handwritten = [], [], []
    for b in boxes:
        p = p_handwritten(image, b)
        if p < settings.HANDWRITING_P_PRINTED:
            printed.append(b)
        elif p > settings.HANDWRITING_P_HANDWRITTEN:
            handwritten.append(b)
        else:
            uncertain.append(b)

    medicine_ctx = doc_type == "prescription"
    regions: list[Region] = []

    # 3. printed → PaddleOCR only
    if printed:
        regions += paddle.recognize(image, printed).regions

    # 4. handwritten → TrOCR (with a PaddleOCR safety net)
    if handwritten:
        if trocr.is_available():
            regions += trocr.recognize(image, handwritten,
                                       medicine_context=medicine_ctx).regions
        else:
            fallback = paddle.recognize(image, handwritten).regions
            for r in fallback:
                r.confidence = min(r.confidence, 0.45)   # force into VERIFY
            regions += fallback

    # 5. uncertain → run BOTH, then resolve
    if uncertain:
        p_res = {tuple(r.bbox): r for r in paddle.recognize(image, uncertain).regions}
        t_res = {}
        if trocr.is_available():
            t_res = {tuple(r.bbox): r
                     for r in trocr.recognize(image, uncertain,
                                              medicine_context=medicine_ctx).regions}
        for b in uncertain:
            regions.append(resolve(p_res.get(tuple(b)), t_res.get(tuple(b)), medicine_ctx))

    # 6. tables — only PaddleOCR can do this, and only lab reports need it
    tables = paddle.extract_tables(image) if doc_type == "lab_report" else []

    h, w = image.shape[:2]
    result = PageResult(page_no=page_no, regions=[r for r in regions if r],
                        tables=tables, width=w, height=h)

    for r in result.regions:
        r.band = band(r.confidence)

    return result
```

## 4.7 Step 6 — Parsing into structured fields

### Lab reports

`parsing/lab_report.py`:

```python
import re
from dataclasses import dataclass

HEADER_SYNONYMS = {
    "test":   ["test", "investigation", "parameter", "analyte", "examination", "test name"],
    "value":  ["result", "value", "observed", "observed value", "found"],
    "unit":   ["unit", "units"],
    "range":  ["reference range", "normal range", "ref range", "bio. ref. interval",
               "biological reference interval", "normal value", "ref. value"],
}

VALUE_RE = re.compile(r"^\s*([<>]?\s*-?\d+(?:[.,]\d+)?)\s*$")
RANGE_RE = re.compile(r"(-?\d+(?:\.\d+)?)\s*[-–to]+\s*(-?\d+(?:\.\d+)?)")


@dataclass
class LabValue:
    test_name: str
    value: float | None
    value_raw: str
    unit: str | None
    ref_low: float | None
    ref_high: float | None
    ref_source: str           # "document" | "builtin" | "none"
    confidence: float
    needs_verification: bool
    bbox: tuple
    page_no: int


def map_columns(header_row: list[str]) -> dict[str, int]:
    mapping = {}
    for idx, cell in enumerate(header_row):
        c = cell.strip().lower()
        for field, synonyms in HEADER_SYNONYMS.items():
            if any(s in c for s in synonyms):
                mapping.setdefault(field, idx)
    return mapping


def parse_table(table: dict, page_no: int) -> list[LabValue]:
    rows = table["res"]["html_rows"]        # shape depends on PaddleOCR version
    if not rows:
        return []

    cols = map_columns(rows[0])
    if "test" not in cols or "value" not in cols:
        return []                            # not a results table — skip it

    out: list[LabValue] = []
    for row in rows[1:]:
        try:
            name = row[cols["test"]].strip()
            raw = row[cols["value"]].strip()
        except IndexError:
            continue
        if not name or not raw:
            continue

        m = VALUE_RE.match(raw.replace(",", ""))
        value = float(m.group(1).replace("<", "").replace(">", "").strip()) if m else None

        unit = row[cols["unit"]].strip() if "unit" in cols and cols["unit"] < len(row) else None

        low = high = None
        source = "none"
        if "range" in cols and cols["range"] < len(row):
            rm = RANGE_RE.search(row[cols["range"]])
            if rm:
                low, high = float(rm.group(1)), float(rm.group(2))
                source = "document"

        if low is None:
            from ..flags.detect import builtin_range
            low, high = builtin_range(name)
            source = "builtin" if low is not None else "none"

        conf = table.get("confidence", 0.9)
        out.append(LabValue(
            test_name=name, value=value, value_raw=raw, unit=unit,
            ref_low=low, ref_high=high, ref_source=source,
            confidence=conf, needs_verification=conf < 0.85,
            bbox=tuple(table["bbox"]), page_no=page_no,
        ))
    return out
```

### Prescriptions

`parsing/prescription.py`:

```python
import re
from dataclasses import dataclass
from ..lexicon.notation import normalize_frequency, normalize_duration, strip_form

STRENGTH_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(mg|mcg|g|ml|iu|units?)\b", re.I)


@dataclass
class Medicine:
    name: str | None
    strength: float | None
    strength_unit: str | None
    frequency: str | None          # OD | BD | TDS | QID | HS | SOS | PRN
    frequency_raw: str | None      # "1-0-1"
    duration_days: int | None
    route: str | None
    form: str | None               # tablet | capsule | syrup | injection
    confidence: float
    needs_verification: bool
    bbox: tuple
    page_no: int
    raw_text: str


def parse_line(text: str, confidence: float, bbox, page_no: int) -> Medicine | None:
    if not text.strip():
        return None

    form, rest = strip_form(text)          # "Tab. Metformin ..." -> ("tablet", "Metformin ...")

    strength = unit = None
    sm = STRENGTH_RE.search(rest)
    if sm:
        strength = float(sm.group(1))
        unit = sm.group(2).lower()
        rest = rest[: sm.start()] + rest[sm.end():]

    freq, freq_raw = normalize_frequency(rest)
    days = normalize_duration(rest)

    # the drug name is what remains after the numbers are removed
    name = re.sub(r"[\d\-/x×]+", " ", rest).strip(" .,-") or None

    return Medicine(
        name=name, strength=strength, strength_unit=unit,
        frequency=freq, frequency_raw=freq_raw, duration_days=days,
        route="oral" if form in ("tablet", "capsule", "syrup") else None,
        form=form, confidence=confidence,
        needs_verification=confidence < 0.85,
        bbox=bbox, page_no=page_no, raw_text=text,
    )
```

`lexicon/notation.py` — Indian prescription notation:

```python
import re

FORMS = {
    "tab": "tablet", "tabs": "tablet", "tablet": "tablet",
    "cap": "capsule", "caps": "capsule", "capsule": "capsule",
    "syp": "syrup", "syr": "syrup", "syrup": "syrup",
    "inj": "injection", "injection": "injection",
    "oint": "ointment", "drops": "drops",
}

DOSE_PATTERN = {
    "1-0-0": "OD",  "0-0-1": "HS",  "0-1-0": "OD",
    "1-0-1": "BD",  "1-1-0": "BD",  "0-1-1": "BD",
    "1-1-1": "TDS", "1-1-1-1": "QID",
}

DURATION_RE = re.compile(
    r"(?:x|×|for)\s*(\d+)\s*(d|day|days|w|wk|week|weeks|m|month|months)\b", re.I)


def strip_form(text: str) -> tuple[str | None, str]:
    m = re.match(r"^\s*([A-Za-z]+)\.?\s+", text)
    if m and m.group(1).lower() in FORMS:
        return FORMS[m.group(1).lower()], text[m.end():]
    return None, text


def normalize_frequency(text: str) -> tuple[str | None, str | None]:
    m = re.search(r"\b(\d(?:-\d){1,3})\b", text)
    if m:
        return DOSE_PATTERN.get(m.group(1)), m.group(1)
    m = re.search(r"\b(OD|BD|BID|TDS|TID|QID|HS|SOS|PRN|STAT|Q\d+H)\b", text, re.I)
    if m:
        token = m.group(1).upper()
        return {"BID": "BD", "TID": "TDS"}.get(token, token), token
    return None, None


def normalize_duration(text: str) -> int | None:
    m = DURATION_RE.search(text)
    if not m:
        return None
    n, unit = int(m.group(1)), m.group(2).lower()
    if unit.startswith("w"):
        return n * 7
    if unit.startswith("m"):
        return n * 30
    return n
```

### Imaging & scan reports — X-ray · Ultrasound · CT · MRI · ECG

**This is a third, genuinely different parsing path.** A lab report is a table of numbers. A
prescription is handwriting. An imaging report is **printed narrative prose with named sections**,
and the doctor reads exactly one of those sections first: the **IMPRESSION**.

#### What we process and what we do not

| Input | Processed? | How |
|---|---|---|
| Ultrasound / sonography report (PDF or photo) | ✅ | printed OCR → section split → impression |
| X-ray report (PDF or photo) | ✅ | printed OCR → section split → impression |
| CT / MRI report (usually multi-page PDF) | ✅ | all pages, then section split across pages |
| ECG report (printed strip header + interpretation) | ✅ | numeric header values + interpretation line |
| Mammography / Doppler / any radiology report | ✅ | same narrative pipeline |
| **The scan IMAGE itself** (the actual X-ray film, the USG frames) | ❌ **stored and displayed, never analysed** | attached to the visit, one tap away for the doctor |
| **DICOM files** (`.dcm`, a scan-centre CD) | ⚠ partial | we read the embedded **structured report / metadata** if present; we never touch pixel data |

> ### The boundary, stated plainly
>
> **We read what the radiologist wrote. We never interpret the scan.**
>
> Reading a printed report is document understanding. Interpreting an X-ray image is a
> different, regulated problem, and this module does not do it. If a judge or a clinician asks,
> that is the answer.

#### Typical report structure we exploit

Almost every Indian radiology report follows this shape, in this order:

```
        ┌──────────────────────────────────────────────┐
        │  <Centre letterhead>                         │  ← header, skip
        │  Patient: …   Age/Sex: …   Ref. by Dr …      │  ← demographics
        │  Study date: 05/08/2026                      │  ← DATE — extract
        ├──────────────────────────────────────────────┤
        │  ULTRASOUND OF WHOLE ABDOMEN                 │  ← MODALITY + REGION
        ├──────────────────────────────────────────────┤
        │  CLINICAL HISTORY / INDICATION               │  ← optional
        │  TECHNIQUE                                   │  ← optional, skip
        ├──────────────────────────────────────────────┤
        │  FINDINGS                                    │  ← full text, keep
        │  Liver is mildly enlarged, measuring 16.2 cm │
        │  with increased echotexture …                │
        ├──────────────────────────────────────────────┤
        │  IMPRESSION / CONCLUSION / OPINION           │  ★★ THE LINE THAT MATTERS
        │  Grade I fatty liver. No focal lesion.       │
        ├──────────────────────────────────────────────┤
        │  ADVICE                                      │  ← optional
        │  Dr. <name>, MD (Radiodiagnosis)             │  ← reporting doctor
        └──────────────────────────────────────────────┘
```

The impression is **1–3 lines out of a 40-line report**, and it is what a doctor with two
minutes reads. Everything else is context they may drill into.

#### The imaging pipeline

```
              IMAGING REPORT (PDF or photo)
                        │
                        ▼
              PDF? → all pages @ 300 DPI
              PHOTO? → single page
                        │
                        ▼
              PaddleOCR — printed path only
              (TrOCR is NOT used here; these are
               printed reports, and a handwritten
               annotation in the margin is noise)
                        │
                        ▼
              MODALITY DETECTION
              keyword + header position
              USG · X-RAY · CT · MRI · ECG · MAMMO · DOPPLER
                        │
                        ▼
              SECTION SPLITTER
              regex on ALL-CAPS section headings,
              tolerant of OCR noise and colons
                        │
        ┌───────────────┼───────────────┬──────────────┐
        ▼               ▼               ▼              ▼
    STUDY DATE      FINDINGS      ★ IMPRESSION      ADVICE
    explicit >      full text     1–3 lines         optional
    inferred >      kept          THE PAYLOAD
    patient-said                        │
        │               │               ▼
        │               │        ATTENTION KEYWORDS
        │               │        scan for terms the
        │               │        doctor should not miss
        │               │        (see §4.8 imaging flags)
        └───────────────┴───────────────┘
                        ▼
              ImagingReport entity
              + the ORIGINAL page image, always attached
```

#### `parsing/imaging_report.py`

```python
import re
from dataclasses import dataclass, field
from datetime import date
from .dates import resolve_date

# ── modality detection ────────────────────────────────────────────────
MODALITY_PATTERNS = [
    ("ULTRASOUND", r"\b(ultra\s*sound|ultrasonograph\w*|u\.?s\.?g\.?|sonograph\w*)\b"),
    ("DOPPLER",    r"\b(doppler|colour\s*doppler|color\s*doppler)\b"),
    ("XRAY",       r"\b(x[\s\-]?ray|radiograph\w*|chest\s*pa\b|skiagram)\b"),
    ("CT",         r"\b(c\.?t\.?\s*scan|computed\s*tomograph\w*|cect|ncct|hrct)\b"),
    ("MRI",        r"\b(m\.?r\.?i\.?|magnetic\s*resonance)\b"),
    ("MAMMOGRAM",  r"\b(mammograph\w*|mammogram)\b"),
    ("ECG",        r"\b(e\.?c\.?g\.?|e\.?k\.?g\.?|electrocardiogram)\b"),
    ("ECHO",       r"\b(echocardiograph\w*|2d\s*echo)\b"),
]

# ── body region, best effort ──────────────────────────────────────────
REGION_PATTERNS = [
    ("abdomen",   r"\b(abdomen|abdominal|whole\s*abdomen|kub)\b"),
    ("chest",     r"\b(chest|thorax|thoracic|lung)\b"),
    ("pelvis",    r"\b(pelvis|pelvic)\b"),
    ("brain",     r"\b(brain|head|cranial|skull)\b"),
    ("spine",     r"\b(spine|spinal|lumbar|cervical|dorsal)\b"),
    ("knee",      r"\b(knee)\b"),
    ("neck",      r"\b(neck|thyroid|carotid)\b"),
    ("obstetric", r"\b(obstetric|foetal|fetal|pregnan\w*|nt\s*scan|anomaly\s*scan)\b"),
]

# ── section headings, tolerant of OCR noise ───────────────────────────
SECTION_HEADINGS = {
    "history":    r"^\s*(clinical\s*(history|details|indication)|indication|history)\s*[:\-–]?\s*$",
    "technique":  r"^\s*(technique|protocol|method)\s*[:\-–]?\s*$",
    "findings":   r"^\s*(findings?|observations?|report|description)\s*[:\-–]?\s*$",
    "impression": r"^\s*(impressions?|conclusions?|opinions?|summary|final\s*impression)\s*[:\-–]?\s*$",
    "advice":     r"^\s*(advice|advis\w*|suggestions?|recommendations?|note)\s*[:\-–]?\s*$",
}
SECTION_RE = {k: re.compile(v, re.I) for k, v in SECTION_HEADINGS.items()}

# some reports put the impression inline: "IMPRESSION: Grade I fatty liver."
INLINE_IMPRESSION_RE = re.compile(
    r"\b(impressions?|conclusions?|opinions?)\s*[:\-–]\s*(.+)", re.I)

DATE_LABEL_RE = re.compile(
    r"\b(study\s*date|date\s*of\s*(study|exam\w*|scan)|scan\s*date|reported\s*on|date)\s*[:\-–]?\s*"
    r"(\d{1,2}[/\-.]\d{1,2}[/\-.]\d{2,4}|\d{4}[/\-.]\d{1,2}[/\-.]\d{1,2})", re.I)

REPORTING_DR_RE = re.compile(
    r"\bdr\.?\s+([A-Z][A-Za-z.\s]{2,40})\b.*?\b(md|dmrd|dnb|radio\w*)\b", re.I)


@dataclass
class ImagingReport:
    modality: str | None                 # ULTRASOUND | XRAY | CT | MRI | ECG | …
    modality_raw: str | None             # the line it was matched on
    body_region: str | None
    study_date: date | None
    date_source: str                     # explicit | inferred | patient | none

    clinical_history: str | None
    technique: str | None
    findings: str | None
    impression: str | None               # ★ the payload
    advice: str | None
    reporting_doctor: str | None

    full_text: str
    attention_terms: list[str] = field(default_factory=list)

    confidence: float = 0.0
    needs_verification: bool = False
    page_range: tuple[int, int] = (1, 1)
    original_page_keys: list[str] = field(default_factory=list)


def _detect(patterns, text: str):
    for label, pattern in patterns:
        m = re.search(pattern, text, re.I)
        if m:
            return label, m.group(0)
    return None, None


def _split_sections(lines: list[str]) -> dict[str, str]:
    """
    Walk the lines. When a line IS a section heading, everything until the next
    heading belongs to that section.
    """
    sections: dict[str, list[str]] = {}
    current = None

    for raw in lines:
        line = raw.strip()
        if not line:
            continue

        matched = None
        for name, rx in SECTION_RE.items():
            if rx.match(line):
                matched = name
                break

        if matched:
            current = matched
            sections.setdefault(current, [])
            continue

        # inline "IMPRESSION: ..." on the same line
        inline = INLINE_IMPRESSION_RE.match(line)
        if inline:
            sections.setdefault("impression", []).append(inline.group(2).strip())
            current = "impression"
            continue

        if current:
            sections[current].append(line)

    return {k: " ".join(v).strip() for k, v in sections.items() if v}


def parse(pages, page_start: int = 1) -> list[ImagingReport]:
    """
    pages: list of PageResult from the OCR router (printed path).
    An imaging report is ONE logical document even when it spans several PDF pages,
    so we join the pages and parse once.
    """
    lines: list[str] = []
    confidences: list[float] = []

    for page in pages:
        for region in sorted(page.regions, key=lambda r: (r.bbox[1], r.bbox[0])):
            if region.text.strip():
                lines.append(region.text.strip())
                confidences.append(region.confidence)

    if not lines:
        return []

    full_text = "\n".join(lines)
    header = "\n".join(lines[:12])          # modality is nearly always near the top

    modality, modality_raw = _detect(MODALITY_PATTERNS, header) or _detect(
        MODALITY_PATTERNS, full_text)
    region, _ = _detect(REGION_PATTERNS, header) or _detect(REGION_PATTERNS, full_text)

    study_date, date_source = resolve_date(full_text, DATE_LABEL_RE)

    sections = _split_sections(lines)

    dr = None
    m = REPORTING_DR_RE.search(full_text)
    if m:
        dr = f"Dr. {m.group(1).strip()}"

    mean_conf = sum(confidences) / len(confidences) if confidences else 0.0

    report = ImagingReport(
        modality=modality,
        modality_raw=modality_raw,
        body_region=region,
        study_date=study_date,
        date_source=date_source,
        clinical_history=sections.get("history"),
        technique=sections.get("technique"),
        findings=sections.get("findings"),
        impression=sections.get("impression"),
        advice=sections.get("advice"),
        reporting_doctor=dr,
        full_text=full_text,
        confidence=mean_conf,
        needs_verification=(mean_conf < 0.85 or sections.get("impression") is None),
        page_range=(page_start, page_start + len(pages) - 1),
    )

    from ..flags.imaging import scan_attention_terms
    report.attention_terms = scan_attention_terms(report.impression or report.findings or "")

    return [report]
```

#### ECG reports — a small special case

An ECG printout carries **numeric header values** plus a one-line machine or cardiologist
interpretation. Both are worth extracting.

```python
# parsing/imaging_report.py  (continued)

ECG_FIELDS = {
    "heart_rate":  r"\b(?:vent\.?\s*rate|heart\s*rate|hr)\s*[:\-]?\s*(\d{2,3})\s*(?:bpm)?",
    "pr_interval": r"\bpr\s*(?:interval)?\s*[:\-]?\s*(\d{2,3})\s*ms",
    "qrs_duration":r"\bqrs\s*(?:duration)?\s*[:\-]?\s*(\d{2,3})\s*ms",
    "qt_qtc":      r"\bqt\s*/?\s*qtc\s*[:\-]?\s*(\d{2,3})\s*/\s*(\d{2,3})\s*ms",
    "axis":        r"\b(?:p[\-\s]?r[\-\s]?t)?\s*axes?\s*[:\-]?\s*([\-\d\s]+)",
}


def parse_ecg(full_text: str) -> dict:
    out = {}
    for key, pattern in ECG_FIELDS.items():
        m = re.search(pattern, full_text, re.I)
        if m:
            out[key] = m.group(1).strip()
    # the interpretation line is usually the last non-empty line before the signature
    m = re.search(r"\b(interpretation|summary)\s*[:\-]?\s*(.+)", full_text, re.I)
    if m:
        out["interpretation"] = m.group(2).strip()
    return out
```

#### DICOM — what we do and do not touch

```python
# parsing/dicom.py
"""
Scan centres sometimes hand the patient a CD of .dcm files.

WE DO:      read the embedded Structured Report (SR) or the text in
            (0008,1030) StudyDescription / (0032,1060) RequestedProcedureDescription,
            and render the first frame as a preview image for the doctor.

WE DO NOT:  analyse pixel data. No measurement, no detection, no classification.
            The image is stored and displayed, nothing more.
"""
import pydicom


def extract_text_only(path: str) -> dict:
    ds = pydicom.dcmread(path, stop_before_pixels=True)   # ← never loads pixels
    return {
        "modality": getattr(ds, "Modality", None),
        "study_description": getattr(ds, "StudyDescription", None),
        "study_date": getattr(ds, "StudyDate", None),
        "body_part": getattr(ds, "BodyPartExamined", None),
        "report_text": _structured_report_text(ds),     # None if no SR present
    }
```

> `stop_before_pixels=True` is not an optimisation. It is the guarantee, in code, that this
> module never reads the image data.

#### What the imaging path outputs

```json
{
  "item_type": "imaging",
  "payload": {
    "modality": "ULTRASOUND",
    "body_region": "abdomen",
    "study_date": "2026-08-05",
    "date_source": "explicit",
    "impression": "Grade I fatty liver. No focal hepatic lesion. Gall bladder normal.",
    "findings": "Liver is mildly enlarged, measuring 16.2 cm with diffusely increased echotexture. Intrahepatic biliary radicles are not dilated. Gall bladder is well distended, wall thickness normal, no calculus …",
    "advice": "Clinical correlation advised.",
    "reporting_doctor": "Dr. R. Menon",
    "attention_terms": ["fatty liver"],
    "page_range": [1, 1]
  },
  "confidence": 0.93,
  "conf_band": "AUTO",
  "needs_verification": false,
  "ocr_engine": "paddleocr",
  "original_page_urls": ["/api/uploads/7a3f.../page/1"]
}
```


## 4.8 Step 7 — Red-flag detection

> **This compares a number to a printed range. It does not diagnose.**

`flags/detect.py`:

```python
import csv
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

RANGES = Path(__file__).parent / "reference_ranges.csv"
CRITICAL = Path(__file__).parent / "critical.csv"


@dataclass
class Flag:
    test_name: str
    value: float
    unit: str | None
    ref_low: float | None
    ref_high: float | None
    severity: str            # "NORMAL" | "LOW" | "HIGH" | "CRITICAL_LOW" | "CRITICAL_HIGH"
    deviation_pct: float | None
    message: str             # a FACT, never a diagnosis
    source: str


@lru_cache(maxsize=1)
def _ranges() -> dict:
    out = {}
    with RANGES.open(encoding="utf-8") as f:
        for r in csv.DictReader(f):
            key = r["test_name"].strip().lower()
            out.setdefault(key, []).append(r)
    return out


def builtin_range(test_name: str, sex: str = "any", age: int | None = None):
    for r in _ranges().get(test_name.strip().lower(), []):
        if r["sex"] not in ("any", sex):
            continue
        if age is not None:
            if r["age_min"] and age < int(r["age_min"]):
                continue
            if r["age_max"] and age > int(r["age_max"]):
                continue
        return float(r["low"]), float(r["high"])
    return None, None


@lru_cache(maxsize=1)
def _critical() -> dict:
    with CRITICAL.open(encoding="utf-8") as f:
        return {r["test_name"].strip().lower(): r for r in csv.DictReader(f)}


def evaluate(lab_value, patient_sex="any", patient_age=None) -> Flag | None:
    if lab_value.value is None:
        return None

    low, high = lab_value.ref_low, lab_value.ref_high
    source = lab_value.ref_source
    if low is None:
        low, high = builtin_range(lab_value.test_name, patient_sex, patient_age)
        source = "builtin" if low is not None else "none"
    if low is None:
        return None                      # no range known — do not guess one

    v = lab_value.value
    crit = _critical().get(lab_value.test_name.strip().lower())

    if crit and crit["panic_low"] and v <= float(crit["panic_low"]):
        severity = "CRITICAL_LOW"
    elif crit and crit["panic_high"] and v >= float(crit["panic_high"]):
        severity = "CRITICAL_HIGH"
    elif v < low:
        severity = "LOW"
    elif v > high:
        severity = "HIGH"
    else:
        severity = "NORMAL"

    if severity == "NORMAL":
        deviation = 0.0
    elif v < low:
        deviation = round((low - v) / low * 100, 1) if low else None
    else:
        deviation = round((v - high) / high * 100, 1) if high else None

    unit = f" {lab_value.unit}" if lab_value.unit else ""
    if severity == "NORMAL":
        msg = f"{lab_value.test_name}: {v}{unit} — within reference range ({low}–{high})."
    elif severity.startswith("CRITICAL"):
        direction = "below" if "LOW" in severity else "above"
        msg = (f"{lab_value.test_name}: {v}{unit} — CRITICALLY {direction} "
               f"the reference range ({low}–{high}).")
    else:
        direction = "below" if severity == "LOW" else "above"
        msg = (f"{lab_value.test_name}: {v}{unit} — {direction} "
               f"the reference range ({low}–{high}).")

    return Flag(lab_value.test_name, v, lab_value.unit, low, high,
                severity, deviation, msg, source)
```

`flags/reference_ranges.csv` (starter — extend it):

```csv
test_name,sex,age_min,age_max,low,high,unit
haemoglobin,male,15,,13.0,17.0,g/dL
haemoglobin,female,15,,12.0,15.0,g/dL
hemoglobin,male,15,,13.0,17.0,g/dL
hemoglobin,female,15,,12.0,15.0,g/dL
wbc,any,,,4000,11000,/µL
total leucocyte count,any,,,4000,11000,/µL
platelet count,any,,,150000,450000,/µL
fasting blood sugar,any,,,70,100,mg/dL
random blood sugar,any,,,70,140,mg/dL
hba1c,any,,,4.0,5.6,%
serum creatinine,male,,,0.7,1.3,mg/dL
serum creatinine,female,,,0.6,1.1,mg/dL
blood urea,any,,,15,40,mg/dL
total cholesterol,any,,,0,200,mg/dL
ldl cholesterol,any,,,0,100,mg/dL
hdl cholesterol,male,,,40,60,mg/dL
triglycerides,any,,,0,150,mg/dL
tsh,any,,,0.4,4.0,mIU/L
sgpt,any,,,7,56,U/L
alt,any,,,7,56,U/L
sgot,any,,,8,48,U/L
ast,any,,,8,48,U/L
total bilirubin,any,,,0.1,1.2,mg/dL
serum sodium,any,,,135,145,mmol/L
serum potassium,any,,,3.5,5.1,mmol/L
```

`flags/critical.csv`:

```csv
test_name,panic_low,panic_high,note
haemoglobin,7.0,20.0,
hemoglobin,7.0,20.0,
platelet count,50000,1000000,
serum potassium,2.5,6.5,
serum sodium,120,160,
fasting blood sugar,50,400,
random blood sugar,50,450,
wbc,2000,30000,
serum creatinine,,5.0,
```

> **Every message in this module is a comparison, not a conclusion.**
> ✅ `"Haemoglobin: 8.2 g/dL — below the reference range (13.0–17.0)."`
> ❌ `"Patient is anaemic."` ← must never be produced


### Imaging reports have no numeric ranges — so what do we flag?

A lab value can be compared against a printed range. **An imaging impression cannot.** There is
no "normal range" for `"Grade I fatty liver"`.

So for imaging we do something different and deliberately weaker: we **scan the impression text
for terms a busy doctor should not scroll past**, and we surface them as *"the report mentions
this"* — never as our own finding.

```
        LAB VALUE                    IMAGING IMPRESSION
        ─────────                    ──────────────────
   10.2 vs range 13.0–17.0        "Grade I fatty liver.
            │                       No focal lesion."
            ▼                              │
   ↓ BELOW REFERENCE RANGE                 ▼
   (arithmetic — objective)        ATTENTION: mentions "fatty liver"
                                   (keyword match on the
                                    radiologist's own words —
                                    NOT our conclusion)
```

`flags/imaging_terms.csv`:

```csv
term,category,note
mass,structural,
lesion,structural,
nodule,structural,
tumou?r,structural,
malignan\w*,structural,
metasta\w*,structural,
fracture,structural,
haemorrhage|hemorrhage,acute,
bleed,acute,
infarct,acute,
ischaemi\w*|ischemi\w*,acute,
thrombus|thrombosis,acute,
embolism,acute,
effusion,fluid,
ascites,fluid,
pneumothorax,acute,
consolidation,structural,
calculus|stone,structural,
obstruction,structural,
dilat\w*,structural,
enlarg\w*|hepatomegaly|splenomegaly|cardiomegaly,structural,
fatty liver|steatosis,structural,
cyst,structural,
stenosis,structural,
aneurysm,acute,
```

`flags/imaging_negation.csv` — terms that **cancel** a match:

```csv
pattern,note
no evidence of,
no focal,
no significant,
not seen,
unremarkable,
within normal limits,
normal study,
no acute,
free of,
ruled out,
```

`flags/imaging.py`:

```python
import csv, re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

TERMS = Path(__file__).parent / "imaging_terms.csv"
NEGATION = Path(__file__).parent / "imaging_negation.csv"

NEG_WINDOW = 60          # characters before the term to look for a negation


@dataclass
class AttentionTerm:
    term: str
    category: str            # structural | acute | fluid
    context: str             # the sentence it appeared in, verbatim
    negated: bool
    message: str             # ALWAYS attributed to the report


@lru_cache(maxsize=1)
def _terms():
    with TERMS.open(encoding="utf-8") as f:
        return [(r["term"], r["category"]) for r in csv.DictReader(f)]


@lru_cache(maxsize=1)
def _negations():
    with NEGATION.open(encoding="utf-8") as f:
        return [r["pattern"] for r in csv.DictReader(f)]


def _is_negated(text: str, start: int) -> bool:
    window = text[max(0, start - NEG_WINDOW):start].lower()
    return any(re.search(p, window) for p in _negations())


def scan_attention_terms(impression: str) -> list[AttentionTerm]:
    """
    Find terms in the RADIOLOGIST'S OWN WORDS that a doctor should not miss.

    This is NOT interpretation. We are not deciding the finding is significant.
    We are saying: the report you have not read yet contains this word.
    """
    if not impression:
        return []

    found: list[AttentionTerm] = []
    seen: set[str] = set()

    for pattern, category in _terms():
        for m in re.finditer(rf"\b{pattern}\b", impression, re.I):
            key = m.group(0).lower()
            if key in seen:
                continue
            seen.add(key)

            negated = _is_negated(impression, m.start())

            # sentence containing the match, verbatim
            left = impression.rfind(".", 0, m.start()) + 1
            right = impression.find(".", m.end())
            sentence = impression[left: right + 1 if right != -1 else None].strip()

            found.append(AttentionTerm(
                term=m.group(0),
                category=category,
                context=sentence,
                negated=negated,
                message=(
                    f'Report states: "{sentence}"' if not negated
                    else f'Report explicitly excludes this: "{sentence}"'
                ),
            ))

    # non-negated first, acute before structural
    order = {"acute": 0, "structural": 1, "fluid": 2}
    return sorted(found, key=lambda t: (t.negated, order.get(t.category, 9)))
```

**What the doctor sees for an imaging report:**

```
④ REPORTS
   2026-08-05   Ultrasound — abdomen                    ⓘ 1 term to note

   IMPRESSION (as reported by Dr. R. Menon)
   "Grade I fatty liver. No focal hepatic lesion. Gall bladder normal."

   ⓘ  Report states: "Grade I fatty liver."
   ✓  Report explicitly excludes this: "No focal hepatic lesion."

   [ view full findings ]   [ view original scan ]
```

Note the phrasing on every line: **"Report states"**, **"as reported by"**. Never *"the patient
has fatty liver"*. The words are the radiologist's, quoted and attributed.

> **A negated term is shown too, and shown as reassurance.** `"No focal lesion"` is clinically
> useful information — hiding it because it is negative would be a worse product.


## 4.9 Step 8 — Summary generation

`summary/generate.py`:

```python
from dataclasses import dataclass
from .templates import render_template
from .safety import assert_safe


@dataclass
class Summary:
    paragraph: str
    red_flags: list[dict]
    normal_count: int
    medicines: list[dict]
    unreadable_count: int
    generated_by: str        # "template" | "llm"


def build(doc_type, lab_values, flags, medicines, imaging, unreadable) -> Summary:
    abnormal = [f for f in flags if f.severity != "NORMAL"]
    critical = [f for f in abnormal if f.severity.startswith("CRITICAL")]

    red_flags = [{
        "severity": f.severity,
        "test": f.test_name,
        "value": f.value,
        "unit": f.unit,
        "range": f"{f.ref_low}–{f.ref_high}",
        "deviation_pct": f.deviation_pct,
        "message": f.message,
        "range_source": f.source,
    } for f in sorted(abnormal, key=lambda x: (not x.severity.startswith("CRITICAL"),
                                               -(x.deviation_pct or 0)))]

    paragraph = render_template(
        doc_type=doc_type,
        total_tests=len(lab_values),
        abnormal=len(abnormal),
        critical=len(critical),
        medicines=medicines,
        imaging=imaging,
        unreadable=unreadable,
    )

    # ★ hard gate — nothing diagnostic leaves this function
    assert_safe(paragraph)
    for rf in red_flags:
        assert_safe(rf["message"])

    return Summary(
        paragraph=paragraph,
        red_flags=red_flags,
        normal_count=len(lab_values) - len(abnormal),
        medicines=[m.__dict__ for m in medicines],
        unreadable_count=unreadable,
        generated_by="template",
    )
```

`summary/templates.py` — deterministic, always available:

```python
def render_template(doc_type, total_tests, abnormal, critical,
                    medicines, imaging, unreadable) -> str:
    parts = []

    if doc_type == "lab_report":
        parts.append(f"Laboratory report with {total_tests} test "
                     f"{'result' if total_tests == 1 else 'results'} extracted.")
        if critical:
            parts.append(f"{critical} value{'s' if critical > 1 else ''} "
                         f"{'are' if critical > 1 else 'is'} critically outside "
                         f"the reference range.")
        if abnormal:
            parts.append(f"{abnormal} of {total_tests} values fall outside "
                         f"the printed reference range.")
        else:
            parts.append("All extracted values are within their reference ranges.")

    elif doc_type == "prescription":
        n = len(medicines)
        parts.append(f"Prescription with {n} medication "
                     f"{'entry' if n == 1 else 'entries'} extracted.")
        named = [m for m in medicines if m.name]
        if named:
            parts.append("Medicines identified: " +
                         ", ".join(f"{m.name} {m.strength or ''}"
                                   f"{m.strength_unit or ''} {m.frequency or ''}".strip()
                                   for m in named[:6]) + ".")

    elif doc_type == "imaging_report":
        # ── the modality and region, in plain words ──
        label = MODALITY_LABEL.get(imaging.get("modality"), "Imaging")
        region = imaging.get("body_region")
        when = imaging.get("study_date") or "an unrecorded date"
        parts.append(f"{label}{f' of the {region}' if region else ''} dated {when}.")

        # ── the impression, QUOTED VERBATIM and attributed ──
        # NOTE: this is the radiologist's own wording. We never paraphrase it.
        #       It goes through assert_safe_quoted(), not assert_safe().
        if imaging.get("impression"):
            parts.append(render_quote(
                imaging["impression"],
                imaging.get("reporting_doctor"),
                source_ref=imaging["source_ref"],
            ))
        else:
            parts.append("No impression section could be located in this report. "
                         "The full findings text and the original scan are attached.")

        # ── attention terms, also as quotations ──
        active = [t for t in imaging.get("attention_terms", []) if not t.negated]
        excluded = [t for t in imaging.get("attention_terms", []) if t.negated]
        if active:
            parts.append(f"{len(active)} term"
                         f"{'s' if len(active) > 1 else ''} in the impression "
                         f"{'are' if len(active) > 1 else 'is'} marked for your attention.")
        if excluded:
            parts.append(f"The report explicitly excludes {len(excluded)} finding"
                         f"{'s' if len(excluded) > 1 else ''}.")

        if imaging.get("modality") == "ECG" and imaging.get("ecg"):
            e = imaging["ecg"]
            bits = []
            if e.get("heart_rate"):   bits.append(f"rate {e['heart_rate']} bpm")
            if e.get("pr_interval"):  bits.append(f"PR {e['pr_interval']} ms")
            if e.get("qrs_duration"): bits.append(f"QRS {e['qrs_duration']} ms")
            if bits:
                parts.append("Recorded values: " + ", ".join(bits) + ".")

    if unreadable:
        parts.append(f"{unreadable} item{'s' if unreadable > 1 else ''} could not be read "
                     f"with sufficient confidence and require doctor verification.")

    parts.append("All values are as printed on the uploaded document. "
                 "Clinical interpretation is for the treating physician.")

    return " ".join(parts)


MODALITY_LABEL = {
    "ULTRASOUND": "Ultrasound report",
    "DOPPLER":    "Doppler study",
    "XRAY":       "X-ray report",
    "CT":         "CT scan report",
    "MRI":        "MRI report",
    "MAMMOGRAM":  "Mammography report",
    "ECG":        "ECG report",
    "ECHO":       "Echocardiography report",
}
```

**What an imaging summary actually reads like:**

```
Ultrasound report of the abdomen dated 2026-08-05.
Report states (as reported by Dr. R. Menon): "Grade I fatty liver.
No focal hepatic lesion. Gall bladder normal."
1 term in the impression is marked for your attention.
The report explicitly excludes 1 finding.
All values are as printed on the uploaded document.
Clinical interpretation is for the treating physician.
```

```
X-ray report of the chest dated 2026-08-05.
Report states: "No focal consolidation. Cardiac silhouette within normal limits.
Costophrenic angles clear."
The report explicitly excludes 1 finding.
All values are as printed on the uploaded document.
Clinical interpretation is for the treating physician.
```

```
ECG report dated 2026-08-05.
Report states: "Sinus rhythm. No acute ST-T changes."
Recorded values: rate 78 bpm, PR 152 ms, QRS 88 ms.
All values are as printed on the uploaded document.
Clinical interpretation is for the treating physician.
```

Every clinical sentence is inside quotation marks and attributed. Nothing is paraphrased.

`summary/safety.py` — the gate:

```python
import re

FORBIDDEN = [
    # diagnostic
    r"\b(diagnos\w*|suggest\w* (a|an|the)? ?\w*(itis|emia|osis|pathy)\b)",
    r"\b(likely|probably|consistent with|indicative of|suggestive of)\s+\w+",
    r"\b(anaemi\w*|anemi\w*|diabet\w*|hypertens\w*|infection|cancer|tumou?r)\b",
    # therapeutic
    r"\b(should (take|start|stop|increase|decrease)|recommend\w*|advis\w*|prescrib\w*)\b",
    r"\b(needs?|requires?)\s+(treatment|medication|surgery|admission)\b",
]
PATTERNS = [re.compile(p, re.I) for p in FORBIDDEN]


class UnsafeOutput(Exception):
    pass


def assert_safe(text: str) -> None:
    """For text WE generated. Diagnostic or therapeutic phrasing is blocked."""
    for p in PATTERNS:
        m = p.search(text)
        if m:
            raise UnsafeOutput(
                f"Blocked diagnostic/therapeutic phrasing: '{m.group(0)}' in: {text[:120]}"
            )
```

> **Fail closed.** If `assert_safe` raises, the pipeline stores the structured values but
> renders **no** summary paragraph, and the doctor sees the raw table with a banner. It never
> ships an unchecked paragraph.

### ⚠ The exception: quoted text from the document itself

An imaging report's IMPRESSION section **is** a clinical conclusion — but it is the
**radiologist's**, already written, already printed on the patient's own document.

```
"Impression: Grade I fatty liver. No focal lesion."
```

Passing that through `assert_safe()` would raise — `fatty liver` and the pattern for a
conclusion both match. **Blocking it would be wrong.** We are not diagnosing; we are showing
the doctor a document their patient handed over, which they would otherwise read themselves.

The distinction is **who wrote it**, and it has to be explicit in code:

```python
# summary/safety.py  (continued)

QUOTE_RE = re.compile(r'^\s*(Report states|As reported by|Impression|Reported impression)\b',
                      re.I)


def assert_safe_quoted(text: str, source_ref: str) -> None:
    """
    For text taken VERBATIM from the uploaded document.

    Allowed, because:
      1. it is the reporting clinician's own wording, not ours
      2. it is attributed, and the source is one tap away
      3. the patient is already carrying this piece of paper

    Still enforced:
      - it must be marked as a quotation
      - it must carry a source reference
      - it must not have been paraphrased, extended or summarised by us
    """
    if not source_ref:
        raise UnsafeOutput("Quoted clinical text with no source reference.")

    if not QUOTE_RE.match(text):
        raise UnsafeOutput(
            f"Clinical text is not marked as a quotation: {text[:120]}"
        )

    # a quotation must actually be quoted — verbatim, inside quote marks
    if '"' not in text and "“" not in text:
        raise UnsafeOutput(
            f"Quoted clinical text is not delimited: {text[:120]}"
        )


def render_quote(sentence: str, reporter: str | None, source_ref: str) -> str:
    """The ONLY sanctioned way clinical text from a document reaches the screen."""
    attribution = f" (as reported by {reporter})" if reporter else ""
    out = f'Report states{attribution}: "{sentence.strip()}"'
    assert_safe_quoted(out, source_ref)
    return out
```

**The rule, in one line:**

| Text | Gate | Why |
|---|---|---|
| Anything **we** generate — paragraphs, comparisons, counts | `assert_safe()` — blocked if diagnostic | it would be our conclusion |
| Text **verbatim from the document**, quoted and attributed | `assert_safe_quoted()` — allowed | it is the radiologist's conclusion, not ours |
| A **paraphrase** of document text | `assert_safe()` — blocked | paraphrasing makes it ours again |

> **Never paraphrase an impression.** The moment you rewrite `"Grade I fatty liver"` as
> `"mild fatty change in the liver"`, it stops being a quotation and becomes our clinical
> statement. Quote it exactly, or do not show it.

## 4.10 Step 9 — Database schema

`models.py`:

```python
from sqlalchemy import (Column, String, Integer, Float, Boolean, DateTime,
                        ForeignKey, Text, JSON, Enum)
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from app.db.base import Base


class Patient(Base):
    __tablename__ = "patients"
    id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id       = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    name_enc      = Column(Text, nullable=False)     # encrypted at column level
    phone_enc     = Column(Text, nullable=False)     # encrypted at column level
    sex           = Column(String(10))
    date_of_birth = Column(DateTime)
    abha_id       = Column(String(20), index=True)
    created_at    = Column(DateTime, default=datetime.utcnow)

    uploads = relationship("Upload", back_populates="patient")


class Upload(Base):
    __tablename__ = "uploads"
    id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id     = Column(UUID(as_uuid=True), ForeignKey("patients.id"),
                            nullable=False, index=True)
    visit_id       = Column(UUID(as_uuid=True), ForeignKey("visits.id"), index=True)
    filename       = Column(String(255), nullable=False)
    mime           = Column(String(64), nullable=False)
    size_bytes     = Column(Integer, nullable=False)
    page_count     = Column(Integer, default=1)

    storage_key    = Column(String(512), nullable=False)   # ORIGINAL — never overwritten
    processed_key  = Column(String(512))
    transform_json = Column(JSON)                          # to map bboxes back

    document_type  = Column(String(32))          # lab_report | prescription | imaging_report | other
    type_confidence= Column(Float)

    status         = Column(String(16), nullable=False, default="QUEUED")
                                                 # QUEUED|PROCESSING|DONE|FAILED|PARTIAL
    error_code     = Column(String(64))
    error_message  = Column(Text)

    job_id         = Column(String(64))
    ocr_engines    = Column(ARRAY(String))       # ["paddleocr","trocr"]
    ocr_duration_ms= Column(Integer)

    uploaded_at    = Column(DateTime, default=datetime.utcnow, index=True)
    processed_at   = Column(DateTime)

    patient  = relationship("Patient", back_populates="uploads")
    reports  = relationship("ExtractedReport", back_populates="upload",
                            cascade="all, delete-orphan")
    summary  = relationship("Summary", back_populates="upload",
                            uselist=False, cascade="all, delete-orphan")


class ExtractedReport(Base):
    """One extracted clinical item — a lab value, a medicine, or an imaging impression."""
    __tablename__ = "extracted_reports"
    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    upload_id   = Column(UUID(as_uuid=True), ForeignKey("uploads.id"),
                         nullable=False, index=True)

    item_type   = Column(String(24), nullable=False)   # lab_value | medicine | imaging | vital
    payload     = Column(JSON, nullable=False)         # shape depends on item_type

    report_date = Column(DateTime)                     # date on the DOCUMENT, not upload time
    date_source = Column(String(16))                   # explicit | inferred | patient | none

    confidence  = Column(Float, nullable=False)
    conf_band   = Column(String(8), nullable=False)    # AUTO | VERIFY | ABSTAIN
    needs_verification = Column(Boolean, default=False)
    verified_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    verified_value = Column(JSON)
    verified_at = Column(DateTime)

    ocr_engine  = Column(String(16))                   # paddleocr | trocr | both
    raw_text    = Column(Text)
    page_no     = Column(Integer, default=1)
    bbox        = Column(ARRAY(Integer))               # ORIGINAL image coordinates
    crop_key    = Column(String(512))                  # "show me the ink"

    created_at  = Column(DateTime, default=datetime.utcnow)

    upload = relationship("Upload", back_populates="reports")


class Summary(Base):
    __tablename__ = "summaries"
    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    upload_id       = Column(UUID(as_uuid=True), ForeignKey("uploads.id"),
                             nullable=False, unique=True, index=True)
    patient_id      = Column(UUID(as_uuid=True), ForeignKey("patients.id"), index=True)

    paragraph       = Column(Text, nullable=False)
    red_flags       = Column(JSON, nullable=False, default=list)
    normal_count    = Column(Integer, default=0)
    abnormal_count  = Column(Integer, default=0)
    critical_count  = Column(Integer, default=0)
    unreadable_count= Column(Integer, default=0)

    generated_by    = Column(String(16), default="template")
    safety_checked  = Column(Boolean, default=False)
    safety_blocked  = Column(Integer, default=0)

    doctor_reviewed = Column(Boolean, default=False)
    reviewed_by     = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    reviewed_at     = Column(DateTime)
    doctor_note     = Column(Text)

    created_at      = Column(DateTime, default=datetime.utcnow)

    upload = relationship("Upload", back_populates="summary")
```

**Indexes to add in the migration:**

```sql
CREATE INDEX idx_uploads_patient_date   ON uploads (patient_id, uploaded_at DESC);
CREATE INDEX idx_uploads_status         ON uploads (status) WHERE status IN ('QUEUED','PROCESSING');
CREATE INDEX idx_reports_upload_type    ON extracted_reports (upload_id, item_type);
CREATE INDEX idx_reports_verify         ON extracted_reports (upload_id) WHERE needs_verification;
CREATE INDEX idx_summaries_patient      ON summaries (patient_id, created_at DESC);
```

## 4.11 Step 10 — The Celery task

`tasks.py`:

```python
import time
from celery import shared_task
from .preprocessing.pipeline import preprocess_pages
from .classifier.document_type import classify
from .engines.router import run_page
from .parsing import lab_report, prescription, imaging_report
from .flags.detect import evaluate
from .summary.generate import build as build_summary
from .summary.safety import UnsafeOutput
from . import repository as repo
from core.realtime import push_to_doctor


@shared_task(bind=True, max_retries=3, default_retry_delay=30, queue="ocr")
def process_upload(self, upload_id: str, patient_id: str):
    started = time.time()
    repo.set_status(upload_id, "PROCESSING")

    try:
        upload = repo.get_upload(upload_id)
        patient = repo.get_patient(patient_id)

        # 1. preprocess — returns processed pages + the inverse transforms
        pages, transforms = preprocess_pages(upload.storage_key, upload.mime)
        repo.save_transforms(upload_id, transforms)

        # 2. classify (page 1 decides the document type)
        doc_type, type_conf = classify(pages[0])
        repo.set_document_type(upload_id, doc_type, type_conf)

        all_items, unreadable = [], 0

        for page_no, image in enumerate(pages, start=1):
            # 3. hybrid OCR
            page = run_page(image, doc_type, page_no)

            # 4. parse by document type
            if doc_type == "lab_report":
                for table in page.tables:
                    all_items += lab_report.parse_table(table, page_no)
            elif doc_type == "prescription":
                for r in page.regions:
                    if r.band == "ABSTAIN":
                        unreadable += 1
                        repo.save_abstention(upload_id, r, page_no,
                                             transforms[page_no - 1], upload.storage_key)
                        continue
                    m = prescription.parse_line(r.text, r.confidence, r.bbox, page_no)
                    if m:
                        all_items.append(m)
            elif doc_type == "imaging_report":
                all_items += imaging_report.parse(page, page_no)

        # 5. red flags
        labs = [i for i in all_items if hasattr(i, "test_name")]
        meds = [i for i in all_items if hasattr(i, "strength_unit")]
        imgs = next((i for i in all_items if isinstance(i, dict)
                     and i.get("modality")), {})

        flags = [f for f in
                 (evaluate(v, patient.sex, patient.age) for v in labs) if f]

        # 6. persist the structured items
        repo.save_items(upload_id, all_items, transforms, upload.storage_key)

        # 7. summary — with the safety gate
        try:
            summary = build_summary(doc_type, labs, flags, meds, imgs, unreadable)
            repo.save_summary(upload_id, patient_id, summary, safety_checked=True)
        except UnsafeOutput as e:
            repo.save_summary_blocked(upload_id, patient_id, reason=str(e))

        repo.set_status(upload_id, "DONE",
                        duration_ms=int((time.time() - started) * 1000),
                        engines=["paddleocr", "trocr"])

        # 8. tell the doctor portal, live
        push_to_doctor(patient_id, {
            "event": "document_processed",
            "upload_id": upload_id,
            "document_type": doc_type,
            "red_flags": len([f for f in flags if f.severity != "NORMAL"]),
            "unreadable": unreadable,
        })

    except Exception as exc:
        repo.set_status(upload_id, "FAILED",
                        error_code=type(exc).__name__, error_message=str(exc)[:500])
        raise self.retry(exc=exc)
```

## 4.12 Step 11 — API endpoints

### Summary table

| Method | Path | Role | Purpose |
|---|---|---|---|
| `POST` | `/api/uploads` | patient | upload a document |
| `GET` | `/api/uploads/{id}` | patient·doctor | processing status + extracted items |
| `GET` | `/api/uploads` | patient | my upload history |
| `GET` | `/api/uploads/{id}/summary` | patient·doctor | summary + red flags |
| `GET` | `/api/uploads/{id}/original` | patient·doctor | presigned URL to the original scan |
| `GET` | `/api/uploads/{id}/crop/{item_id}` | doctor | "show me the ink" crop |
| `GET` | `/api/doctor/patients/{pid}/uploads` | doctor | all uploads for one patient |
| `POST` | `/api/doctor/items/{item_id}/verify` | doctor | confirm an unreadable item |
| `POST` | `/api/doctor/summaries/{id}/review` | doctor | mark reviewed + add a note |
| `WS` | `/ws/doctor/{doctor_id}` | doctor | live push when processing finishes |

---

### `POST /api/uploads`

**Request** — `multipart/form-data`

```
Authorization: Bearer <patient_jwt>
Content-Type: multipart/form-data

file: <binary>          (jpg | png | webp | pdf, ≤ 25 MB)
visit_id: <uuid>        (optional)
```

**Response `202 Accepted`**

```json
{
  "upload_id": "9f1c2b64-3a7e-4c11-8f2a-1d9e5b7c4a30",
  "job_id": "celery-7d2f8a1c",
  "status": "QUEUED",
  "filename": "blood_report_aug2026.pdf",
  "page_count": 2,
  "poll_url": "/api/uploads/9f1c2b64-3a7e-4c11-8f2a-1d9e5b7c4a30"
}
```

**Error `422`**

```json
{
  "error": {
    "code": "FILE_TOO_LARGE",
    "message": "File is larger than 25 MB.",
    "request_id": "req_8c1e5a2b"
  }
}
```

---

### `GET /api/uploads/{upload_id}`

**Response `200` — while processing**

```json
{
  "upload_id": "9f1c2b64-3a7e-4c11-8f2a-1d9e5b7c4a30",
  "status": "PROCESSING",
  "filename": "blood_report_aug2026.pdf",
  "uploaded_at": "2026-09-03T14:22:07+05:30",
  "document_type": null,
  "progress": { "pages_done": 1, "pages_total": 2 }
}
```

**Response `200` — complete**

```json
{
  "upload_id": "9f1c2b64-3a7e-4c11-8f2a-1d9e5b7c4a30",
  "status": "DONE",
  "filename": "blood_report_aug2026.pdf",
  "uploaded_at": "2026-09-03T14:22:07+05:30",
  "processed_at": "2026-09-03T14:22:16+05:30",
  "ocr_duration_ms": 8420,
  "ocr_engines": ["paddleocr", "trocr"],
  "document_type": "lab_report",
  "type_confidence": 0.94,
  "report_date": "2026-08-05",
  "original_url": "/api/uploads/9f1c2b64.../original",
  "items": [
    {
      "id": "a1b2c3d4-0000-4000-8000-000000000001",
      "item_type": "lab_value",
      "payload": {
        "test_name": "Haemoglobin",
        "value": 10.2,
        "unit": "g/dL",
        "ref_low": 13.0,
        "ref_high": 17.0,
        "ref_source": "document"
      },
      "confidence": 0.96,
      "conf_band": "AUTO",
      "needs_verification": false,
      "ocr_engine": "paddleocr",
      "page_no": 1,
      "bbox": [412, 588, 260, 34]
    },
    {
      "id": "a1b2c3d4-0000-4000-8000-000000000002",
      "item_type": "lab_value",
      "payload": {
        "test_name": "Total Leucocyte Count",
        "value": 7800,
        "unit": "/µL",
        "ref_low": 4000,
        "ref_high": 11000,
        "ref_source": "document"
      },
      "confidence": 0.94,
      "conf_band": "AUTO",
      "needs_verification": false,
      "ocr_engine": "paddleocr",
      "page_no": 1,
      "bbox": [412, 624, 260, 34]
    },
    {
      "id": "a1b2c3d4-0000-4000-8000-000000000003",
      "item_type": "medicine",
      "payload": {
        "name": null,
        "raw_ocr_guess": "Melformn 50?",
        "strength": null,
        "frequency": null
      },
      "confidence": 0.41,
      "conf_band": "ABSTAIN",
      "needs_verification": true,
      "ocr_engine": "trocr",
      "page_no": 2,
      "bbox": [180, 412, 340, 36],
      "crop_url": "/api/uploads/9f1c2b64.../crop/a1b2c3d4-0000-4000-8000-000000000003"
    }
  ]
}
```

---

### `GET /api/uploads`  (patient's own history)

**Query:** `?limit=20&cursor=<opaque>&status=DONE`

**Response `200`**

```json
{
  "uploads": [
    {
      "upload_id": "9f1c2b64-3a7e-4c11-8f2a-1d9e5b7c4a30",
      "filename": "blood_report_aug2026.pdf",
      "document_type": "lab_report",
      "status": "DONE",
      "uploaded_at": "2026-09-03T14:22:07+05:30",
      "report_date": "2026-08-05",
      "red_flag_count": 1,
      "thumbnail_url": "/api/uploads/9f1c2b64.../thumbnail"
    },
    {
      "upload_id": "5e8a1f22-9c3d-4b77-a1e0-6f4b2c8d9e11",
      "filename": "prescription_dr_sharma.jpg",
      "document_type": "prescription",
      "status": "DONE",
      "uploaded_at": "2026-09-03T14:19:41+05:30",
      "report_date": "2026-04-12",
      "red_flag_count": 0,
      "thumbnail_url": "/api/uploads/5e8a1f22.../thumbnail"
    }
  ],
  "next_cursor": null,
  "total": 2
}
```

---

### `GET /api/uploads/{upload_id}/summary`

**Response `200`**

```json
{
  "upload_id": "9f1c2b64-3a7e-4c11-8f2a-1d9e5b7c4a30",
  "document_type": "lab_report",
  "report_date": "2026-08-05",

  "paragraph": "Laboratory report with 8 test results extracted. 1 of 8 values falls outside the printed reference range. All values are as printed on the uploaded document. Clinical interpretation is for the treating physician.",

  "red_flags": [
    {
      "severity": "LOW",
      "test": "Haemoglobin",
      "value": 10.2,
      "unit": "g/dL",
      "range": "13.0–17.0",
      "deviation_pct": 21.5,
      "message": "Haemoglobin: 10.2 g/dL — below the reference range (13.0–17.0).",
      "range_source": "document"
    }
  ],

  "counts": {
    "normal": 7,
    "abnormal": 1,
    "critical": 0,
    "unreadable": 0
  },

  "generated_by": "template",
  "safety_checked": true,
  "safety_blocked": 0,

  "doctor_reviewed": false,
  "original_url": "/api/uploads/9f1c2b64.../original"
}
```

**Response `200` — an IMAGING report (ultrasound, X-ray, CT, MRI, ECG)**

Note the different shape: no numeric ranges, an `impression` block that is **verbatim and
attributed**, and `attention_terms` instead of `red_flags`.

```json
{
  "upload_id": "7a3f8e12-b455-4c90-9d21-3e6f8a1b2c44",
  "document_type": "imaging_report",
  "report_date": "2026-08-05",

  "imaging": {
    "modality": "ULTRASOUND",
    "modality_label": "Ultrasound report",
    "body_region": "abdomen",
    "reporting_doctor": "Dr. R. Menon",
    "impression_quoted": "Report states (as reported by Dr. R. Menon): \"Grade I fatty liver. No focal hepatic lesion. Gall bladder normal.\"",
    "impression_raw": "Grade I fatty liver. No focal hepatic lesion. Gall bladder normal.",
    "findings_raw": "Liver is mildly enlarged, measuring 16.2 cm with diffusely increased echotexture. Intrahepatic biliary radicles are not dilated. Gall bladder is well distended, wall thickness normal, no calculus seen. Both kidneys are normal in size, shape and echotexture.",
    "advice": "Clinical correlation advised.",
    "page_count": 1
  },

  "paragraph": "Ultrasound report of the abdomen dated 2026-08-05. Report states (as reported by Dr. R. Menon): \"Grade I fatty liver. No focal hepatic lesion. Gall bladder normal.\" 1 term in the impression is marked for your attention. The report explicitly excludes 1 finding. All values are as printed on the uploaded document. Clinical interpretation is for the treating physician.",

  "red_flags": [],

  "attention_terms": [
    {
      "term": "fatty liver",
      "category": "structural",
      "negated": false,
      "context": "Grade I fatty liver.",
      "message": "Report states: \"Grade I fatty liver.\""
    },
    {
      "term": "lesion",
      "category": "structural",
      "negated": true,
      "context": "No focal hepatic lesion.",
      "message": "Report explicitly excludes this: \"No focal hepatic lesion.\""
    }
  ],

  "counts": { "normal": 0, "abnormal": 0, "critical": 0, "unreadable": 0,
              "attention": 1, "excluded": 1 },

  "generated_by": "template",
  "safety_checked": true,
  "quoted_text_verified": true,
  "safety_blocked": 0,

  "doctor_reviewed": false,
  "original_url": "/api/uploads/7a3f8e12.../original",
  "page_urls": ["/api/uploads/7a3f8e12.../page/1"]
}
```

**Response `200` — an ECG report**

```json
{
  "upload_id": "b21d9c04-77aa-4e33-8812-9f0a5c7e1d88",
  "document_type": "imaging_report",
  "report_date": "2026-08-05",

  "imaging": {
    "modality": "ECG",
    "modality_label": "ECG report",
    "body_region": null,
    "impression_quoted": "Report states: \"Sinus rhythm. No acute ST-T changes.\"",
    "impression_raw": "Sinus rhythm. No acute ST-T changes.",
    "ecg": {
      "heart_rate": "78",
      "pr_interval": "152",
      "qrs_duration": "88",
      "qt_qtc": "384/412",
      "interpretation": "Sinus rhythm. No acute ST-T changes."
    }
  },

  "paragraph": "ECG report dated 2026-08-05. Report states: \"Sinus rhythm. No acute ST-T changes.\" Recorded values: rate 78 bpm, PR 152 ms, QRS 88 ms. All values are as printed on the uploaded document. Clinical interpretation is for the treating physician.",

  "attention_terms": [
    { "term": "acute", "category": "acute", "negated": true,
      "context": "No acute ST-T changes.",
      "message": "Report explicitly excludes this: \"No acute ST-T changes.\"" }
  ],

  "counts": { "attention": 0, "excluded": 1, "unreadable": 0 },
  "original_url": "/api/uploads/b21d9c04.../original"
}
```

---

### `GET /api/uploads/{upload_id}/original`

**Response `200`**

```json
{
  "url": "https://s3.local/mk-originals/…?X-Amz-Expires=900&X-Amz-Signature=…",
  "mime": "application/pdf",
  "expires_in": 900
}
```

> Presigned, expires in 15 minutes, and only issued to the owning patient or a doctor with an
> active visit for that patient.

---

### `POST /api/doctor/items/{item_id}/verify`

**Request**

```json
{
  "corrected_value": {
    "name": "Metformin",
    "strength": 500,
    "strength_unit": "mg",
    "frequency": "BD"
  }
}
```

**Response `200`**

```json
{
  "item_id": "a1b2c3d4-0000-4000-8000-000000000003",
  "verified": true,
  "verified_by": "dr_sharma",
  "verified_at": "2026-09-03T14:31:02+05:30",
  "training_pair_stored": true
}
```

> Every verification is stored as a labelled training pair — the crop image plus what the
> doctor said it actually was. This is how the handwriting model improves over time.

---

### `GET /api/doctor/patients/{patient_id}/uploads`

**Response `200`**

```json
{
  "patient": {
    "id": "c7d8e9f0-1111-4222-8333-444455556666",
    "name": "Aarav Sharma",
    "age": 42,
    "sex": "male"
  },
  "uploads": [
    {
      "upload_id": "9f1c2b64-3a7e-4c11-8f2a-1d9e5b7c4a30",
      "filename": "blood_report_aug2026.pdf",
      "document_type": "lab_report",
      "report_date": "2026-08-05",
      "status": "DONE",
      "red_flag_count": 1,
      "highest_severity": "LOW",
      "unreadable_count": 0,
      "summary_url": "/api/uploads/9f1c2b64.../summary"
    }
  ],
  "timeline": [
    { "date": "2025-04-12", "type": "prescription", "text": "Metformin 500 mg BD started" },
    { "date": "2026-01-14", "type": "lab_value",    "text": "HbA1c 9.2 % (above range)" },
    { "date": "2026-08-05", "type": "lab_value",    "text": "HbA1c 8.6 % (above range, improving)" }
  ]
}
```

---

# 5. Frontend — Patient Portal

## 5.1 Upload UI

**File:** `frontend/patient_app/src/documents/Upload.tsx`

```tsx
import { useCallback, useState } from "react";
import { useDropzone } from "react-dropzone";
import { uploadDocument } from "../../shared/api/documents";

type FileState = {
  id: string;
  file: File;
  status: "pending" | "uploading" | "queued" | "processing" | "done" | "failed";
  progress: number;
  uploadId?: string;
  error?: string;
};

const ACCEPTED = {
  "image/jpeg": [".jpg", ".jpeg"],
  "image/png": [".png"],
  "image/webp": [".webp"],
  "application/pdf": [".pdf"],
};
const MAX_BYTES = 25 * 1024 * 1024;

export default function Upload() {
  const [files, setFiles] = useState<FileState[]>([]);

  const onDrop = useCallback((accepted: File[]) => {
    const next = accepted.map((f) => ({
      id: crypto.randomUUID(),
      file: f,
      status: "pending" as const,
      progress: 0,
    }));
    setFiles((prev) => [...prev, ...next]);
    next.forEach(send);
  }, []);

  async function send(fs: FileState) {
    setFiles((p) => p.map((f) => (f.id === fs.id ? { ...f, status: "uploading" } : f)));
    try {
      const res = await uploadDocument(fs.file, (pct) =>
        setFiles((p) => p.map((f) => (f.id === fs.id ? { ...f, progress: pct } : f)))
      );
      setFiles((p) =>
        p.map((f) =>
          f.id === fs.id
            ? { ...f, status: "queued", uploadId: res.upload_id, progress: 100 }
            : f
        )
      );
      poll(fs.id, res.upload_id);
    } catch (e: any) {
      setFiles((p) =>
        p.map((f) =>
          f.id === fs.id
            ? { ...f, status: "failed", error: e?.response?.data?.error?.message ?? "Upload failed" }
            : f
        )
      );
    }
  }

  function poll(localId: string, uploadId: string) {
    const timer = setInterval(async () => {
      const r = await fetch(`/api/uploads/${uploadId}`).then((x) => x.json());
      setFiles((p) =>
        p.map((f) =>
          f.id === localId ? { ...f, status: r.status.toLowerCase() } : f
        )
      );
      if (["DONE", "FAILED"].includes(r.status)) clearInterval(timer);
    }, 2000);
  }

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: ACCEPTED,
    maxSize: MAX_BYTES,
    multiple: true,
  });

  return (
    <div className="p-6 max-w-2xl mx-auto">
      <h1 className="text-3xl font-semibold mb-2">Upload your reports</h1>
      <p className="text-lg text-gray-600 mb-6">
        Prescriptions, blood reports, lab reports, scan reports. Photos or PDF.
      </p>

      <div
        {...getRootProps()}
        className={`border-4 border-dashed rounded-xl p-12 text-center cursor-pointer
                    transition ${isDragActive ? "border-blue-500 bg-blue-50" : "border-gray-300"}`}
      >
        <input {...getInputProps()} />
        <div className="text-6xl mb-4">📄</div>
        <p className="text-xl font-medium">Tap here to choose files</p>
        <p className="text-gray-500 mt-2">or drag them in</p>
        <p className="text-sm text-gray-400 mt-4">JPG · PNG · PDF · up to 25 MB each</p>
      </div>

      <div className="mt-8 space-y-3">
        {files.map((f) => (
          <FileRow key={f.id} state={f} />
        ))}
      </div>

      {files.some((f) => f.status === "done") && (
        <button className="mt-8 w-full py-4 text-xl bg-green-600 text-white rounded-lg">
          I have uploaded everything
        </button>
      )}
    </div>
  );
}
```

## 5.2 Upload status states

```tsx
const STATUS: Record<string, { label: string; color: string; icon: string }> = {
  pending:    { label: "Waiting",        color: "text-gray-500",   icon: "⏳" },
  uploading:  { label: "Uploading…",     color: "text-blue-600",   icon: "⬆️" },
  queued:     { label: "In queue",       color: "text-blue-600",   icon: "📥" },
  processing: { label: "Reading your document…", color: "text-amber-600", icon: "🔍" },
  done:       { label: "Ready",          color: "text-green-600",  icon: "✅" },
  failed:     { label: "Could not read", color: "text-red-600",    icon: "⚠️" },
};

function FileRow({ state }: { state: FileState }) {
  const s = STATUS[state.status];
  return (
    <div className="flex items-center gap-4 p-4 border rounded-lg">
      <span className="text-3xl">{s.icon}</span>
      <div className="flex-1 min-w-0">
        <p className="font-medium truncate">{state.file.name}</p>
        <p className={`text-sm ${s.color}`}>{s.label}</p>
        {state.status === "uploading" && (
          <div className="h-2 bg-gray-200 rounded mt-2">
            <div
              className="h-2 bg-blue-600 rounded transition-all"
              style={{ width: `${state.progress}%` }}
            />
          </div>
        )}
        {state.error && <p className="text-sm text-red-600 mt-1">{state.error}</p>}
      </div>
    </div>
  );
}
```

> **The patient never waits for OCR.** Upload completes in under a second; processing status
> updates in the background. They can keep adding documents while earlier ones process.

## 5.3 Upload history

**File:** `frontend/patient_app/src/documents/History.tsx`

```tsx
import { useEffect, useState } from "react";
import { listUploads } from "../../shared/api/documents";

export default function History() {
  const [uploads, setUploads] = useState<any[]>([]);

  useEffect(() => { listUploads().then((r) => setUploads(r.uploads)); }, []);

  return (
    <div className="p-6 max-w-2xl mx-auto">
      <h1 className="text-3xl font-semibold mb-6">My documents</h1>

      {uploads.length === 0 && (
        <p className="text-gray-500">You have not uploaded any documents yet.</p>
      )}

      <div className="space-y-3">
        {uploads.map((u) => (
          <a key={u.upload_id} href={`/documents/${u.upload_id}`}
             className="flex gap-4 p-4 border rounded-lg hover:bg-gray-50">
            <img src={u.thumbnail_url} alt="" className="w-16 h-20 object-cover rounded border" />
            <div className="flex-1">
              <p className="font-medium">{u.filename}</p>
              <p className="text-sm text-gray-600">
                {DOC_LABEL[u.document_type] ?? "Document"}
                {u.report_date && ` · ${u.report_date}`}
              </p>
              {u.red_flag_count > 0 && (
                <span className="inline-block mt-2 px-2 py-1 text-xs rounded
                                 bg-amber-100 text-amber-800">
                  {u.red_flag_count} value{u.red_flag_count > 1 ? "s" : ""} outside range
                </span>
              )}
            </div>
          </a>
        ))}
      </div>
    </div>
  );
}

const DOC_LABEL: Record<string, string> = {
  lab_report: "Lab report",
  prescription: "Prescription",
  imaging_report: "Scan report",
  other: "Document",
};
```

> **Note on what the patient sees:** the patient sees *which values were outside the printed
> range*, never an interpretation. No "you may be anaemic". Same rule as the doctor side.

---

# 6. Frontend — Doctor Portal

## 6.1 List of a patient's uploads

**File:** `frontend/doctor_portal/src/sections/Reports.tsx`

```tsx
import { useEffect, useState } from "react";
import { getPatientUploads } from "../../shared/api/doctor";

export default function Reports({ patientId }: { patientId: string }) {
  const [data, setData] = useState<any>(null);
  const [openId, setOpenId] = useState<string | null>(null);

  useEffect(() => { getPatientUploads(patientId).then(setData); }, [patientId]);
  if (!data) return <div className="p-4 text-gray-500">Loading reports…</div>;

  return (
    <section className="border-t pt-4">
      <h2 className="text-sm font-semibold uppercase tracking-wide text-gray-500 mb-3">
        ④ Reports
      </h2>

      <table className="w-full text-sm">
        <thead className="text-left text-gray-500 border-b">
          <tr>
            <th className="py-2 w-28">Date</th>
            <th className="w-32">Type</th>
            <th>File</th>
            <th className="w-40">Flags</th>
            <th className="w-24"></th>
          </tr>
        </thead>
        <tbody>
          {data.uploads.map((u: any) => (
            <>
              <tr key={u.upload_id}
                  className="border-b hover:bg-gray-50 cursor-pointer"
                  onClick={() => setOpenId(openId === u.upload_id ? null : u.upload_id)}>
                <td className="py-2 tabular-nums">{u.report_date ?? "—"}</td>
                <td>{DOC_LABEL[u.document_type]}</td>
                <td className="truncate">{u.filename}</td>
                <td>
                  {u.red_flag_count > 0 ? (
                    <SeverityPill severity={u.highest_severity} count={u.red_flag_count} />
                  ) : (
                    <span className="text-gray-400">none</span>
                  )}
                  {u.unreadable_count > 0 && (
                    <span className="ml-2 text-xs text-gray-600">
                      ⚠ {u.unreadable_count} unread
                    </span>
                  )}
                </td>
                <td className="text-blue-600">{openId === u.upload_id ? "Hide" : "Open"}</td>
              </tr>

              {openId === u.upload_id && (
                <tr>
                  <td colSpan={5} className="bg-gray-50 p-0">
                    <SummaryPanel uploadId={u.upload_id} />
                  </td>
                </tr>
              )}
            </>
          ))}
        </tbody>
      </table>
    </section>
  );
}
```

## 6.2 Summary panel — paragraph + colour-coded red flags

**File:** `frontend/doctor_portal/src/sections/SummaryPanel.tsx`

```tsx
import { useEffect, useState } from "react";
import { getSummary, getOriginalUrl } from "../../shared/api/doctor";

const SEVERITY = {
  CRITICAL_HIGH: { bg: "bg-red-50",    border: "border-l-4 border-red-600",
                   text: "text-red-800",   icon: "🚨", label: "CRITICAL — above range" },
  CRITICAL_LOW:  { bg: "bg-red-50",    border: "border-l-4 border-red-600",
                   text: "text-red-800",   icon: "🚨", label: "CRITICAL — below range" },
  HIGH:          { bg: "bg-amber-50",  border: "border-l-4 border-amber-500",
                   text: "text-amber-900", icon: "↑",  label: "Above range" },
  LOW:           { bg: "bg-amber-50",  border: "border-l-4 border-amber-500",
                   text: "text-amber-900", icon: "↓",  label: "Below range" },
} as const;

export default function SummaryPanel({ uploadId }: { uploadId: string }) {
  const [s, setS] = useState<any>(null);

  useEffect(() => { getSummary(uploadId).then(setS); }, [uploadId]);
  if (!s) return <div className="p-4 text-gray-500">Loading summary…</div>;

  return (
    <div className="p-5 space-y-5">

      {/* ── short paragraph summary ── */}
      <div>
        <h4 className="text-xs uppercase tracking-wide text-gray-500 mb-2">Summary</h4>
        <p className="text-[15px] leading-relaxed text-gray-900 max-w-3xl">
          {s.paragraph}
        </p>
      </div>

      {/* ── colour-coded red-flag bullets ── */}
      {s.red_flags.length > 0 && (
        <div>
          <h4 className="text-xs uppercase tracking-wide text-gray-500 mb-2">
            Values outside reference range
          </h4>
          <ul className="space-y-2">
            {s.red_flags.map((f: any, i: number) => {
              const st = SEVERITY[f.severity as keyof typeof SEVERITY];
              return (
                <li key={i} className={`${st.bg} ${st.border} ${st.text} rounded-r px-4 py-3`}>
                  <div className="flex items-start gap-3">
                    <span className="text-lg leading-none">{st.icon}</span>
                    <div className="flex-1">
                      <div className="font-semibold">
                        {f.test}: {f.value}{f.unit ? ` ${f.unit}` : ""}
                        <span className="ml-2 text-xs font-normal opacity-70">
                          {st.label} · reference {f.range}
                        </span>
                      </div>
                      {f.deviation_pct != null && (
                        <div className="text-xs opacity-70 mt-0.5 tabular-nums">
                          {f.deviation_pct}% outside the range
                          {f.range_source === "builtin" && " · range not printed on the report"}
                        </div>
                      )}
                    </div>
                  </div>
                </li>
              );
            })}
          </ul>
        </div>
      )}

      {s.red_flags.length === 0 && (
        <div className="bg-green-50 border-l-4 border-green-500 text-green-800 rounded-r px-4 py-3">
          ✅ All {s.counts.normal} extracted values are within their reference ranges.
        </div>
      )}

      {/* ── unreadable items ── */}
      {s.counts.unreadable > 0 && (
        <div className="bg-gray-100 border-l-4 border-gray-400 rounded-r px-4 py-3">
          <span className="font-medium">
            ⚠ {s.counts.unreadable} item{s.counts.unreadable > 1 ? "s" : ""} could not be read
          </span>
          <p className="text-sm text-gray-600 mt-1">
            The system did not have enough confidence to extract a value.
            View the original to read it yourself.
          </p>
        </div>
      )}

      {/* ── link back to the original scan ── */}
      <div className="pt-2 border-t flex gap-3">
        <button
          onClick={async () => window.open((await getOriginalUrl(uploadId)).url, "_blank")}
          className="px-4 py-2 border rounded text-sm hover:bg-gray-50"
        >
          📄 View original scan
        </button>
        <button className="px-4 py-2 border rounded text-sm hover:bg-gray-50">
          ✓ Mark reviewed
        </button>
      </div>

      <p className="text-xs text-gray-400 pt-1">
        Values are as printed on the uploaded document. Clinical interpretation is for the
        treating physician.
      </p>
    </div>
  );
}
```

## 6.3 Imaging report panel — a different shape

An imaging report has no numeric values to colour-code. It has **one quoted impression** and a
set of attention terms. It renders differently, and it must be visually obvious that the
clinical words are the radiologist's, not ours.

**File:** `frontend/doctor_portal/src/sections/ImagingPanel.tsx`

```tsx
import { useState } from "react";

const MODALITY_ICON: Record<string, string> = {
  ULTRASOUND: "🔊", DOPPLER: "🔊", XRAY: "🩻", CT: "🧠",
  MRI: "🧲", MAMMOGRAM: "🎗️", ECG: "💓", ECHO: "💓",
};

export default function ImagingPanel({ data }: { data: any }) {
  const [showFindings, setShowFindings] = useState(false);
  const img = data.imaging;
  const active = data.attention_terms.filter((t: any) => !t.negated);
  const excluded = data.attention_terms.filter((t: any) => t.negated);

  return (
    <div className="p-5 space-y-5">

      {/* ── header ── */}
      <div className="flex items-baseline gap-3">
        <span className="text-2xl">{MODALITY_ICON[img.modality] ?? "📄"}</span>
        <div>
          <h3 className="font-semibold text-lg">
            {img.modality_label}
            {img.body_region && <span className="font-normal"> — {img.body_region}</span>}
          </h3>
          <p className="text-sm text-gray-500 tabular-nums">
            {data.report_date}
            {img.reporting_doctor && ` · ${img.reporting_doctor}`}
          </p>
        </div>
      </div>

      {/* ── THE IMPRESSION — quoted, attributed, visually set apart ── */}
      <blockquote className="border-l-4 border-slate-400 bg-slate-50 pl-4 py-3 pr-4 rounded-r">
        <div className="text-xs uppercase tracking-wide text-slate-500 mb-1">
          Impression — as written on the report
        </div>
        <p className="text-[15px] leading-relaxed text-slate-900 italic">
          “{img.impression_raw}”
        </p>
        {img.reporting_doctor && (
          <footer className="text-xs text-slate-500 mt-2">— {img.reporting_doctor}</footer>
        )}
      </blockquote>

      {/* ── attention terms ── */}
      {active.length > 0 && (
        <div>
          <h4 className="text-xs uppercase tracking-wide text-gray-500 mb-2">
            Marked for your attention
          </h4>
          <ul className="space-y-2">
            {active.map((t: any, i: number) => (
              <li key={i}
                  className="bg-blue-50 border-l-4 border-blue-500 text-blue-900
                             rounded-r px-4 py-3">
                <span className="text-lg mr-2">ⓘ</span>
                <span className="italic">“{t.context}”</span>
                <span className="ml-2 text-xs opacity-60">({t.category})</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* ── explicitly excluded — shown as reassurance, not hidden ── */}
      {excluded.length > 0 && (
        <div>
          <h4 className="text-xs uppercase tracking-wide text-gray-500 mb-2">
            Explicitly excluded by the report
          </h4>
          <ul className="space-y-1">
            {excluded.map((t: any, i: number) => (
              <li key={i} className="text-sm text-green-800 flex gap-2">
                <span>✓</span><span className="italic">“{t.context}”</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* ── full findings, collapsed by default ── */}
      {img.findings_raw && (
        <div>
          <button onClick={() => setShowFindings(!showFindings)}
                  className="text-sm text-blue-600 underline">
            {showFindings ? "Hide" : "Show"} full findings
          </button>
          {showFindings && (
            <p className="mt-2 text-sm text-gray-700 leading-relaxed
                          bg-gray-50 p-3 rounded whitespace-pre-wrap">
              {img.findings_raw}
            </p>
          )}
        </div>
      )}

      {img.advice && (
        <p className="text-sm text-gray-600">
          <span className="font-medium">Advice on the report:</span> “{img.advice}”
        </p>
      )}

      {/* ── the scan itself — displayed, never analysed ── */}
      <div className="pt-3 border-t flex gap-3">
        <button className="px-4 py-2 border rounded text-sm hover:bg-gray-50">
          🩻 View the scan report
        </button>
        {img.page_count > 1 && (
          <span className="text-sm text-gray-500 self-center">
            {img.page_count} pages
          </span>
        )}
      </div>

      <p className="text-xs text-gray-400">
        Text shown above is quoted from the uploaded report. This system does not interpret
        scan images. Clinical interpretation is for the treating physician.
      </p>
    </div>
  );
}
```

**The visual rules that matter here:**

| | Why |
|---|---|
| The impression is a `<blockquote>`, italic, in quote marks, with an attribution footer | it must be unmistakable that these are the radiologist's words, not the system's |
| Attention terms are **blue `ⓘ`**, not red `🚨` | red means "we detected a problem". Blue means "the report mentions this". We are not making a clinical judgement. |
| Excluded findings are shown, in green, not hidden | `"No focal lesion"` is useful information; suppressing negatives would make the product worse |
| Full findings collapsed by default | the doctor wants the impression; the findings are there when they drill in |
| A footer disclaiming image interpretation, on every imaging panel | the boundary, stated where it is seen |

## 6.4 The "show me the ink" viewer

```tsx
function UnreadableItem({ item }: { item: any }) {
  const [showCrop, setShowCrop] = useState(false);
  return (
    <div className="border rounded p-3 bg-gray-50">
      <div className="flex justify-between items-center">
        <div>
          <span className="text-gray-600">Could not read this line</span>
          {item.payload.raw_ocr_guess && (
            <span className="ml-2 text-xs text-gray-400 font-mono">
              best guess: "{item.payload.raw_ocr_guess}" · {Math.round(item.confidence * 100)}%
            </span>
          )}
        </div>
        <button onClick={() => setShowCrop(!showCrop)}
                className="text-sm text-blue-600 underline">
          {showCrop ? "Hide" : "Show me the ink"}
        </button>
      </div>
      {showCrop && (
        <img src={item.crop_url} alt="original region"
             className="mt-3 border rounded max-w-full" />
      )}
    </div>
  );
}
```

---

# 7. End-to-End Connectivity

## 7.1 The full request path

```
PATIENT BROWSER                BACKEND                    WORKER            DOCTOR BROWSER
      │                           │                          │                    │
 1.   ├─ POST /api/auth/login ───►│                          │                    │
      │◄─ { access_token } ───────┤                          │                    │
      │   stored in memory        │                          │                    │
      │                           │                          │                    │
 2.   ├─ POST /api/uploads ──────►│                          │                    │
      │   Bearer <patient_jwt>    │ validate magic bytes     │                    │
      │   multipart file          │ store ORIGINAL → S3      │                    │
      │                           │ INSERT uploads row       │                    │
      │                           ├─ enqueue ───────────────►│                    │
      │◄─ 202 { upload_id } ──────┤                          │                    │
      │   ~300 ms                 │                          │                    │
      │                           │                          │                    │
 3.   │                           │                   preprocess pages            │
      │                           │                   classify document           │
      │                           │                   PaddleOCR detect            │
      │                           │                   handwriting classify        │
      │                           │                   route → Paddle / TrOCR      │
      │                           │                   merge + confidence          │
      │                           │                   parse → flag → summarize    │
      │                           │◄─ write rows ────────────┤                    │
      │                           │                          │                    │
 4.   ├─ GET /api/uploads/{id} ──►│                          │                    │
      │   poll every 2 s          │                          │                    │
      │◄─ { status: "DONE" } ─────┤                          │                    │
      │                           │                          │                    │
 5.   │                           ├─ WS push ───────────────────────────────────►│
      │                           │  { event: "document_processed" }              │
      │                           │                          │      doctor's ④ Reports
      │                           │                          │      section refreshes LIVE
      │                           │                          │                    │
 6.   │                           │◄─ GET /api/doctor/patients/{pid}/uploads ─────┤
      │                           │   Bearer <doctor_jwt>                         │
      │                           ├──────────────────────────────────────────────►│
      │                           │                          │                    │
 7.   │                           │◄─ GET /api/uploads/{id}/summary ──────────────┤
      │                           ├─ paragraph + red_flags ──────────────────────►│
      │                           │                          │                    │
 8.   │                           │◄─ GET /api/uploads/{id}/original ─────────────┤
      │                           ├─ presigned S3 URL, 15 min ───────────────────►│
```

## 7.2 Auth and session handling

**Token issue** — one endpoint, two roles:

```python
# modules/01-authentication/session/jwt.py
from datetime import datetime, timedelta
from jose import jwt
from core.config import settings


def issue(user_id: str, role: str, patient_id: str | None = None) -> str:
    return jwt.encode(
        {
            "sub": str(user_id),
            "role": role,                      # "PATIENT" | "DOCTOR"
            "pid": str(patient_id) if patient_id else None,
            "exp": datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_MINUTES),
            "iat": datetime.utcnow(),
        },
        settings.JWT_SECRET,
        algorithm="HS256",
    )
```

**Route guards** — the scoping happens here, not in the UI:

```python
# app/core/auth.py
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from core.config import settings

bearer = HTTPBearer()


def _decode(cred: HTTPAuthorizationCredentials = Depends(bearer)) -> dict:
    try:
        return jwt.decode(cred.credentials, settings.JWT_SECRET, algorithms=["HS256"])
    except JWTError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token")


def current_patient(claims: dict = Depends(_decode)):
    if claims["role"] != "PATIENT":
        raise HTTPException(403, "Patient access required")
    return get_patient(claims["pid"])


def current_doctor(claims: dict = Depends(_decode)):
    if claims["role"] != "DOCTOR":
        raise HTTPException(403, "Doctor access required")
    return get_doctor(claims["sub"])
```

**Ownership check on every document read:**

```python
def assert_can_read_upload(upload, actor) -> None:
    if actor.role == "PATIENT":
        if upload.patient_id != actor.patient_id:
            raise HTTPException(403, "Not your document")
    elif actor.role == "DOCTOR":
        if not has_active_visit(actor.id, upload.patient_id):
            raise HTTPException(403, "No active visit with this patient")
    else:
        raise HTTPException(403, "Forbidden")
```

| Rule | Enforced where |
|---|---|
| A patient reads only their own uploads | repository layer, not just the route |
| A doctor reads only patients with an active visit | `assert_can_read_upload` |
| Original-file URLs are presigned and expire in 15 min | `upload/store.py` |
| Every original access writes an audit row | `repository.py` |

## 7.3 File storage layout

```
mk-originals/                        ← NEVER overwritten, all crops derive from here
  {patient_id}/{upload_id}/original.pdf
  {patient_id}/{upload_id}/original.jpg

mk-processed/                        ← what the OCR engines saw
  {patient_id}/{upload_id}/page-1.png
  {patient_id}/{upload_id}/page-2.png
  {patient_id}/{upload_id}/transform.json

mk-crops/                            ← "show me the ink"
  {patient_id}/{upload_id}/{item_id}.png

mk-thumbs/
  {patient_id}/{upload_id}/thumb.jpg
```

**Retention:**

| Object | Kept until |
|---|---|
| `mk-originals/` | per hospital record-retention policy — this is the clinical record |
| `mk-processed/` | 7 days (regeneratable from the original) |
| `mk-crops/` | as long as the item exists — the doctor may need to re-check |
| `mk-thumbs/` | as long as the upload exists |

**Local-disk alternative** (no MinIO) — swap the storage adapter only:

```python
# upload/store.py
if settings.STORAGE_BACKEND == "local":
    ROOT = Path(settings.LOCAL_STORAGE_PATH)   # e.g. ./storage
    def put_original(key, data, mime):
        p = ROOT / "originals" / key
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
        return str(p)
```

## 7.4 How the doctor portal gets live data

```python
# app/core/realtime.py
from fastapi import WebSocket
from collections import defaultdict

_connections: dict[str, set[WebSocket]] = defaultdict(set)


async def register(doctor_id: str, ws: WebSocket):
    await ws.accept()
    _connections[doctor_id].add(ws)


def unregister(doctor_id: str, ws: WebSocket):
    _connections[doctor_id].discard(ws)


async def push_to_doctor(patient_id: str, payload: dict):
    for doctor_id in doctors_with_active_visit(patient_id):
        for ws in list(_connections[doctor_id]):
            try:
                await ws.send_json(payload)
            except Exception:
                unregister(doctor_id, ws)
```

Frontend subscription:

```ts
// shared/ws/socket.ts
export function connectDoctor(doctorId: string, token: string, onEvent: (e: any) => void) {
  let ws: WebSocket;
  let retry = 1000;

  const open = () => {
    ws = new WebSocket(`${import.meta.env.VITE_WS_URL}/doctor/${doctorId}?token=${token}`);
    ws.onmessage = (m) => onEvent(JSON.parse(m.data));
    ws.onopen = () => { retry = 1000; };
    ws.onclose = () => {
      setTimeout(open, retry);
      retry = Math.min(retry * 2, 30000);      // exponential backoff, capped
    };
  };

  open();
  return () => ws?.close();
}
```

**Fallback:** if the WebSocket cannot connect, the doctor portal polls
`GET /api/doctor/patients/{pid}/uploads` every 10 seconds. Degraded, but never broken.

---

# 8. Testing Steps

## 8.1 Prepare sample files

Create `backend/03-document-ocr/tests/corpus/`:

```
corpus/
├── lab/
│   ├── cbc_clean_printed.jpg          crisp scan, clear table
│   ├── lft_photo_angled.jpg           phone photo, perspective distortion
│   ├── thyroid_faded_thermal.jpg      faded thermal paper
│   └── full_panel_2page.pdf           multi-page PDF
├── prescription/
│   ├── rx_clear_handwriting.jpg       legible handwriting
│   ├── rx_messy_handwriting.jpg       ★ the hard one — expect abstentions
│   ├── rx_mixed_printed_hand.jpg      printed letterhead + handwritten drugs
│   └── rx_hindi_english_mixed.jpg
├── imaging/
│   ├── usg_abdomen.pdf                single-page sonography report
│   ├── usg_obstetric_photo.jpg        phone photo of an USG report
│   ├── xray_chest_report.jpg          printed X-ray report
│   ├── xray_knee_report.pdf
│   ├── ct_brain_3page.pdf             ★ multi-page — impression on page 3
│   ├── mri_lumbar_spine.pdf
│   ├── ecg_report.jpg                 rate/PR/QRS header + interpretation
│   ├── echo_2d.pdf
│   └── usg_no_impression_section.jpg  ★ edge case — no IMPRESSION heading
├── edge/
│   ├── blurry_unusable.jpg            should be rejected at QC
│   ├── upside_down.jpg                orientation correction test
│   ├── duplicate_of_cbc.jpg           dedup test
│   └── not_medical.jpg                should classify as "other"
└── labels.jsonl                       ground truth
```

`labels.jsonl` format:

```json
{"file":"lab/cbc_clean_printed.jpg","doc_type":"lab_report","report_date":"2026-08-05","items":[{"type":"lab_value","test_name":"Haemoglobin","value":10.2,"unit":"g/dL","ref_low":13.0,"ref_high":17.0},{"type":"lab_value","test_name":"Total Leucocyte Count","value":7800,"unit":"/µL","ref_low":4000,"ref_high":11000}]}
{"file":"prescription/rx_clear_handwriting.jpg","doc_type":"prescription","report_date":"2026-04-12","items":[{"type":"medicine","name":"Metformin","strength":500,"strength_unit":"mg","frequency":"BD","duration_days":30}]}
```

> **Anonymise before committing.** Black out names, phone numbers and hospital IDs. Never
> commit an identifiable patient document.

## 8.2 Unit tests

```bash
cd backend
pytest modules/03-document-ocr/tests -v
```

**The critical one — bbox round-trip:**

```python
# tests/test_bbox_roundtrip.py
import cv2, numpy as np
from modules.document_ocr.preprocessing.pipeline import preprocess_page
from modules.document_ocr.preprocessing.transform import to_original_coords


def test_bbox_maps_back_to_original():
    """
    The most common defect in a pipeline of this shape:
    a bbox found on the DESKEWED image, used to crop the ORIGINAL,
    gives the wrong region and 'show me the ink' shows the wrong ink.
    """
    original = cv2.imread("tests/corpus/lab/lft_photo_angled.jpg")

    # draw a marker at a known location
    cv2.rectangle(original, (400, 600), (700, 640), (0, 0, 255), -1)

    processed, transform = preprocess_page(original)

    # find the marker in the PROCESSED image
    mask = cv2.inRange(processed, (0, 0, 200), (80, 80, 255))
    x, y, w, h = cv2.boundingRect(mask)

    # map it BACK to original coordinates
    ox, oy, ow, oh = to_original_coords((x, y, w, h), transform)

    assert abs(ox - 400) < 15, f"x drifted: {ox} vs 400"
    assert abs(oy - 600) < 15, f"y drifted: {oy} vs 600"
```

**Notation parsing:**

```python
# tests/test_notation.py
import pytest
from modules.document_ocr.lexicon.notation import (
    normalize_frequency, normalize_duration, strip_form)

@pytest.mark.parametrize("text,expected", [
    ("1-0-1",     "BD"),
    ("1-1-1",     "TDS"),
    ("0-0-1",     "HS"),
    ("1-1-1-1",   "QID"),
    ("BD",        "BD"),
    ("BID",       "BD"),
    ("TID",       "TDS"),
])
def test_frequency(text, expected):
    assert normalize_frequency(text)[0] == expected


@pytest.mark.parametrize("text,days", [
    ("x5d", 5), ("x 10 days", 10), ("for 2 weeks", 14), ("x1m", 30),
])
def test_duration(text, days):
    assert normalize_duration(text) == days


def test_form():
    assert strip_form("Tab. Metformin 500mg")[0] == "tablet"
    assert strip_form("Syp. Ambroxol")[0] == "syrup"
```

**Abstention behaviour:**

```python
# tests/test_abstention.py
from modules.document_ocr.lexicon.snap import snap_to_formulary


def test_snaps_a_near_miss():
    name, score = snap_to_formulary("Melformin")
    assert name == "Metformin"
    assert score >= 0.75


def test_abstains_on_nonsense():
    name, score = snap_to_formulary("Xqzzyphen")
    assert name is None, "Must ABSTAIN, never invent a medicine"
```

**Red-flag detection:**

```python
# tests/test_flags.py
from modules.document_ocr.flags.detect import evaluate
from modules.document_ocr.parsing.lab_report import LabValue


def make(name, value, low, high, unit="g/dL"):
    return LabValue(name, value, str(value), unit, low, high,
                    "document", 0.95, False, (0, 0, 0, 0), 1)


def test_below_range():
    f = evaluate(make("Haemoglobin", 10.2, 13.0, 17.0))
    assert f.severity == "LOW"
    assert "below the reference range" in f.message


def test_within_range():
    assert evaluate(make("Haemoglobin", 14.0, 13.0, 17.0)).severity == "NORMAL"


def test_critical():
    assert evaluate(make("Haemoglobin", 6.1, 13.0, 17.0)).severity == "CRITICAL_LOW"


def test_message_is_never_a_diagnosis():
    """The single most important test in this module."""
    f = evaluate(make("Haemoglobin", 6.1, 13.0, 17.0))
    forbidden = ["anaemi", "anemi", "diagnos", "suggest", "likely",
                 "should", "recommend", "treat"]
    assert not any(w in f.message.lower() for w in forbidden), \
        f"Diagnostic language leaked: {f.message}"
```

**Imaging report parsing:**

```python
# tests/test_imaging.py
import pytest
from modules.document_ocr.parsing.imaging_report import parse, parse_ecg
from modules.document_ocr.flags.imaging import scan_attention_terms
from tests.helpers import ocr_pages


def test_modality_and_region():
    r = parse(ocr_pages("imaging/usg_abdomen.pdf"))[0]
    assert r.modality == "ULTRASOUND"
    assert r.body_region == "abdomen"
    assert r.study_date is not None
    assert r.date_source == "explicit"


def test_impression_extracted_verbatim():
    r = parse(ocr_pages("imaging/usg_abdomen.pdf"))[0]
    assert r.impression is not None
    assert "fatty liver" in r.impression.lower()
    # it must be the DOCUMENT's words, not a paraphrase
    assert r.impression in r.full_text


def test_multipage_impression_on_last_page():
    """CT reports often put FINDINGS on pages 1–2 and IMPRESSION on page 3."""
    r = parse(ocr_pages("imaging/ct_brain_3page.pdf"))[0]
    assert r.impression is not None, "Impression must be found across page breaks"
    assert r.page_range == (1, 3)


def test_missing_impression_section_does_not_crash():
    r = parse(ocr_pages("imaging/usg_no_impression_section.jpg"))[0]
    assert r.impression is None
    assert r.findings is not None, "Fall back to findings text"
    assert r.needs_verification is True


def test_ecg_numeric_fields():
    e = parse_ecg(open("tests/corpus/imaging/ecg_report.txt").read())
    assert e["heart_rate"] == "78"
    assert e["pr_interval"] == "152"
    assert "sinus rhythm" in e["interpretation"].lower()


# ── attention terms ──────────────────────────────────────────────

def test_positive_term_detected():
    terms = scan_attention_terms("Grade I fatty liver. Gall bladder normal.")
    hits = [t for t in terms if not t.negated]
    assert any("fatty liver" in t.term.lower() for t in hits)


def test_negation_is_detected_not_alarmed():
    terms = scan_attention_terms("No focal hepatic lesion is seen.")
    lesion = next(t for t in terms if "lesion" in t.term.lower())
    assert lesion.negated is True, "'No focal lesion' must NOT read as a positive finding"
    assert "excludes" in lesion.message.lower()


def test_negation_window_does_not_over_reach():
    """A negation 200 characters earlier must not cancel a later positive finding."""
    text = ("No pleural effusion. " + "Lungs are clear. " * 12 +
            "There is a 2 cm mass in the right upper lobe.")
    terms = scan_attention_terms(text)
    mass = next(t for t in terms if t.term.lower() == "mass")
    assert mass.negated is False, "Distant negation must not suppress a real finding"


def test_message_always_attributes_to_the_report():
    for t in scan_attention_terms("Grade I fatty liver. No focal lesion."):
        assert t.message.lower().startswith("report "), \
            f"Attention message must attribute to the report, got: {t.message}"
```

**Safety gate — including the quoted-text exception:**

```python
# tests/test_safety.py
import pytest
from modules.document_ocr.summary.safety import assert_safe, UnsafeOutput

SAFE = [
    "Haemoglobin: 10.2 g/dL — below the reference range (13.0–17.0).",
    "Laboratory report with 8 test results extracted.",
    "Prescription lists Metformin 500 mg twice daily for 30 days.",
]

UNSAFE = [
    "Findings suggest anaemia.",
    "The patient is likely diabetic.",
    "Patient should start iron supplementation.",
    "This is consistent with an infection.",
    "Recommend a repeat CBC in two weeks.",
]

@pytest.mark.parametrize("t", SAFE)
def test_safe_passes(t):
    assert_safe(t)

@pytest.mark.parametrize("t", UNSAFE)
def test_unsafe_blocked(t):
    with pytest.raises(UnsafeOutput):
        assert_safe(t)


# ── the quoted-text exception ─────────────────────────────────────────
from modules.document_ocr.summary.safety import assert_safe_quoted, render_quote


def test_generated_diagnosis_is_blocked():
    """If WE write it, it is blocked — even if it is true."""
    with pytest.raises(UnsafeOutput):
        assert_safe("The patient has Grade I fatty liver.")


def test_quoted_radiologist_impression_is_allowed():
    """
    An imaging report's IMPRESSION *is* a clinical conclusion — but it is the
    radiologist's, already printed on the patient's own document. Blocking it
    would be wrong: the doctor would otherwise read it themselves.
    """
    quoted = render_quote(
        "Grade I fatty liver. No focal hepatic lesion.",
        reporter="Dr. R. Menon",
        source_ref="upload:7a3f8e12/page:1",
    )
    assert_safe_quoted(quoted, "upload:7a3f8e12/page:1")
    assert quoted.startswith("Report states")
    assert '"' in quoted


def test_quote_without_source_reference_is_blocked():
    with pytest.raises(UnsafeOutput):
        assert_safe_quoted('Report states: "Grade I fatty liver."', source_ref="")


def test_quote_without_attribution_marker_is_blocked():
    with pytest.raises(UnsafeOutput):
        assert_safe_quoted('Grade I fatty liver.', source_ref="upload:7a3f/page:1")


def test_quote_without_quote_marks_is_blocked():
    with pytest.raises(UnsafeOutput):
        assert_safe_quoted("Report states: Grade I fatty liver.",
                           source_ref="upload:7a3f/page:1")


def test_paraphrase_of_an_impression_is_blocked():
    """
    Rewriting 'Grade I fatty liver' as 'mild fatty change in the liver'
    makes it OUR statement again. Quote exactly, or do not show it.
    """
    with pytest.raises(UnsafeOutput):
        assert_safe("There is mild fatty change in the liver.")
```

## 8.3 Benchmark the two engines

```bash
python -m modules.document_ocr.engines.benchmark \
  --corpus modules/03-document-ocr/tests/corpus \
  --labels modules/03-document-ocr/tests/corpus/labels.jsonl \
  --out benchmark.md
```

Expected output shape:

```markdown
| Metric                        | PaddleOCR only | TrOCR only | HYBRID |
|-------------------------------|----------------|------------|--------|
| Printed CER                   | 0.031          | 0.184      | 0.031  |
| Handwriting CER               | 0.412          | 0.147      | 0.147  |
| Lab test↔value pairing        | 0.94           | 0.11       | 0.94   |
| Medicine name accuracy        | 0.38           | 0.71       | 0.79   |
| Dose + frequency accuracy     | 0.44           | 0.62       | 0.74   |
| CORRECT abstention rate       | —              | —          | 0.86   |
| Mean seconds per page (CPU)   | 2.1            | 14.7       | 4.3    |
```

> **Report all seven rows, including the ones where we are weak.** The last row —
> *how often we correctly refused to guess* — is the honest and most defensible number.

## 8.4 Manual end-to-end test

```bash
# 1. Start everything
docker compose up --build
# wait for: "Application startup complete"

# 2. Verify health
curl http://localhost:8000/health
curl http://localhost:8000/ready       # 200 ONLY when both OCR models are loaded

# 3. Seed a demo patient and doctor
docker compose exec backend python -m 06-platform.database.seed --demo
# prints:  patient: +919876543210 / OTP 123456
#          doctor:  dr.sharma@demo.in / demo1234
```

**Then, in the browser:**

| # | Do this | Expect |
|---|---|---|
| 1 | Open http://localhost:3000, log in as the demo patient | Home screen |
| 2 | Go to Upload, drag in `cbc_clean_printed.jpg` | Progress bar → "In queue" within ~1 s |
| 3 | Watch the status chip | "Reading your document…" → "Ready" in 5–15 s |
| 4 | Upload `rx_messy_handwriting.jpg` | Also completes; some items marked unreadable |
| 5 | Open "My documents" | Both files listed with type and date |
| 6 | Open http://localhost:3001, log in as the demo doctor | Patient list |
| 7 | Open the demo patient → **④ Reports** | Both uploads listed, newest first |
| 8 | Click the lab report row | Summary paragraph + red-flag bullets |
| 9 | Check the Haemoglobin bullet | Amber, `↓ Below range`, `reference 13.0–17.0` |
| 10 | Click the prescription row | ⚠ *"1 item could not be read"* |
| 11 | Click **Show me the ink** | The cropped handwriting appears — **verify it is the right region** |
| 12 | Click **View original scan** | Original opens in a new tab; URL expires in 15 min |
| 13 | Log in as a *different* doctor with no visit | `403` on the summary endpoint |
| 14 | Log in as a *different* patient | The first patient's uploads are not listed |

**Failure drills — run all of these before any demo:**

```bash
# TrOCR unavailable → PaddleOCR fallback, confidence capped into VERIFY
docker compose exec worker python -c "import os; os.environ['TROCR_MODEL']='does-not-exist'"
# upload a prescription → items appear with needs_verification=true, nothing crashes

# Worker down → uploads queue and drain on restart
docker compose stop worker
# upload → status stays QUEUED, no error to the patient
docker compose start worker
# → processes automatically

# Blurry unusable file
# upload edge/blurry_unusable.jpg
# → accepted anyway, whole page marked for verification, image shown to the doctor

# Safety gate
docker compose exec backend pytest modules/03-document-ocr/tests/test_safety.py -v
# → all UNSAFE strings blocked
```

---

# 9. Folder Structure Tree

```
medikiosk/
│
├── README.md
├── docker-compose.yml
├── .env.example
├── Makefile
├── .gitignore
│
├── docs/
│   ├── ARCHITECTURE.md
│   ├── API_SPEC.md
│   └── DATA_CONTRACTS.md
│
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── alembic.ini
│   ├── pytest.ini
│   ├── .env
│   │
│   └── app/
│       ├── main.py                      FastAPI entrypoint
│       ├── worker.py                    Celery app
│       │
│       ├── core/
│       │   ├── config.py                settings, validated at boot
│       │   ├── auth.py                  JWT guards, ownership checks
│       │   ├── realtime.py              WebSocket hub
│       │   ├── storage.py               S3 / local adapter
│       │   └── logging.py               structured logs + PII redaction
│       │
│       ├── db/
│       │   ├── base.py
│       │   ├── session.py
│       │   ├── seed.py
│       │   └── migrations/
│       │       ├── env.py
│       │       └── versions/
│       │           ├── 001_users.py
│       │           ├── 002_patients_visits.py
│       │           ├── 003_questionnaire.py
│       │           ├── 004_documents.py       ← this module
│       │           └── 005_summaries.py       ← this module
│       │
│       └── modules/
│           ├── 01-authentication/
│           ├── 02-questionnaire/
│           │
│           ├── 03-document-ocr/          ★ THIS MODULE
│           │   ├── OCR_MODULE.md               this document
│           │   ├── README.md
│           │   ├── __init__.py
│           │   ├── tasks.py                    the Celery pipeline
│           │   ├── models.py                   SQLAlchemy tables
│           │   ├── repository.py               all DB access
│           │   │
│           │   ├── api/
│           │   │   ├── routes.py
│           │   │   └── schemas.py
│           │   │
│           │   ├── upload/
│           │   │   ├── validate.py             magic bytes, size, pages
│           │   │   ├── store.py                S3 / local put + presign
│           │   │   └── enqueue.py
│           │   │
│           │   ├── preprocessing/
│           │   │   ├── pdf.py                  pdf2image @ 300 DPI
│           │   │   ├── pipeline.py             the 9-step chain
│           │   │   ├── deskew.py
│           │   │   ├── perspective.py
│           │   │   ├── shadow.py
│           │   │   └── transform.py            ★ invert → original coords
│           │   │
│           │   ├── classifier/
│           │   │   ├── document_type.py
│           │   │   └── handwriting.py          per-region P(handwritten)
│           │   │
│           │   ├── engines/
│           │   │   ├── base.py                 ★ OCRProvider interface
│           │   │   ├── paddle_engine.py        ★ ENGINE 1
│           │   │   ├── trocr_engine.py         ★ ENGINE 2
│           │   │   ├── cloud_engine.py         optional, disabled
│           │   │   ├── router.py               ★ region → engine routing
│           │   │   ├── merge.py                ★ confidence + resolution
│           │   │   └── benchmark.py
│           │   │
│           │   ├── lexicon/
│           │   │   ├── formulary.txt           ~15k Indian medicines
│           │   │   ├── lab_tests.txt
│           │   │   ├── snap.py                 fuzzy match
│           │   │   └── notation.py             1-0-1 · x5d · Tab. · SOS
│           │   │
│           │   ├── parsing/
│           │   │   ├── lab_report.py
│           │   │   ├── prescription.py
│           │   │   ├── imaging_report.py
│           │   │   └── dates.py
│           │   │
│           │   ├── flags/
│           │   │   ├── reference_ranges.csv
│           │   │   ├── critical.csv
│           │   │   ├── detect.py               ★ value vs range
│           │   │   └── trends.py
│           │   │
│           │   ├── summary/
│           │   │   ├── generate.py
│           │   │   ├── templates.py
│           │   │   └── safety.py               ★ blocks diagnostic phrasing
│           │   │
│           │   └── tests/
│           │       ├── test_preprocessing.py
│           │       ├── test_bbox_roundtrip.py  ★ the crop test
│           │       ├── test_merge.py
│           │       ├── test_notation.py
│           │       ├── test_abstention.py
│           │       ├── test_flags.py
│           │       ├── test_safety.py
│           │       └── corpus/
│           │           ├── lab/
│           │           ├── prescription/
│           │           ├── imaging/
│           │           ├── edge/
│           │           └── labels.jsonl
│           │
│           ├── 04-summary-engine/
│           ├── 05-doctor-portal/
│           └── 06-platform/
│
├── frontend/
│   ├── shared/
│   │   ├── api/
│   │   │   ├── client.ts                 base fetch, auth, errors
│   │   │   ├── documents.ts              upload · list · status · summary
│   │   │   └── doctor.ts
│   │   ├── ws/
│   │   │   └── socket.ts                 reconnecting WebSocket
│   │   └── ui/
│   │       ├── tokens.css
│   │       ├── patient.css               huge, spoken, icon-driven
│   │       └── clinical.css              dense, structured
│   │
│   ├── patient_app/
│   │   ├── Dockerfile
│   │   ├── package.json
│   │   ├── vite.config.ts
│   │   ├── .env
│   │   └── src/
│   │       ├── main.tsx
│   │       ├── App.tsx
│   │       ├── auth/
│   │       ├── questionnaire/
│   │       └── documents/
│   │           ├── Upload.tsx            ★ drag-drop + camera
│   │           ├── FileRow.tsx           ★ progress / status states
│   │           ├── History.tsx           ★ my uploaded documents
│   │           └── DocumentDetail.tsx
│   │
│   └── doctor_portal/
│       ├── Dockerfile
│       ├── package.json
│       ├── vite.config.ts
│       ├── .env
│       └── src/
│           ├── main.tsx
│           ├── App.tsx
│           ├── pages/
│           │   ├── Login.tsx
│           │   ├── PatientList.tsx
│           │   └── PatientView.tsx
│           └── sections/
│               ├── BasicInfo.tsx         ①
│               ├── Summary.tsx           ②
│               ├── Questionnaire.tsx     ③
│               ├── Reports.tsx           ④ ★ upload list
│               ├── SummaryPanel.tsx      ★ paragraph + red flags
│               ├── UnreadableItem.tsx    ★ show me the ink
│               └── SeverityPill.tsx
│
└── storage/                              local-disk fallback for MinIO
    ├── originals/
    ├── processed/
    └── crops/
```

---

# 10. Run Instructions

## 10.1 Fastest path — Docker Compose

```bash
# 1. Clone and configure
git clone <your-repo> medikiosk
cd medikiosk
cp .env.example backend/.env
# edit backend/.env — at minimum set POSTGRES_PASSWORD and JWT_SECRET

# 2. Build and start everything
docker compose up --build
# first build takes 10–20 minutes — it bakes the OCR models into the image

# 3. In a second terminal: migrate and seed
docker compose exec backend alembic upgrade head
docker compose exec backend python -m 06-platform.database.seed --demo

# 4. Verify
curl http://localhost:8000/health
curl http://localhost:8000/ready        # 200 only when BOTH OCR models are loaded
```

| Service | URL |
|---|---|
| Backend API | http://localhost:8000 |
| Interactive API docs | http://localhost:8000/docs |
| Patient app | http://localhost:3000 |
| Doctor portal | http://localhost:3001 |
| MinIO console | http://localhost:9001 |

## 10.2 Manual path — three terminals

**Terminal 1 — infrastructure**

```bash
docker run -d --name mk-pg -p 5432:5432 \
  -e POSTGRES_DB=medikiosk -e POSTGRES_USER=medikiosk \
  -e POSTGRES_PASSWORD=change_me postgres:16-alpine

docker run -d --name mk-redis -p 6379:6379 redis:7-alpine

docker run -d --name mk-minio -p 9000:9000 -p 9001:9001 \
  -e MINIO_ROOT_USER=medikiosk -e MINIO_ROOT_PASSWORD=change_me_12345 \
  minio/minio:latest server /data --console-address ":9001"
```

**Terminal 2 — backend API**

```bash
cd backend
source .venv/bin/activate            # Windows: .\.venv\Scripts\Activate.ps1

alembic upgrade head
python -m 06-platform.database.seed --demo

uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Expect:

```
INFO:     Loading PaddleOCR models…
INFO:     Loading TrOCR microsoft/trocr-base-handwritten…
INFO:     Both OCR engines ready
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

**Terminal 3 — the OCR worker**

```bash
cd backend
source .venv/bin/activate

celery -A workers.celery_app worker -l info -Q ocr --concurrency=2
```

Expect:

```
[config]
.> app:         medikiosk
.> transport:   redis://localhost:6379/1
.> concurrency: 2 (prefork)
[queues]
.> ocr          exchange=ocr(direct) key=ocr
[tasks]
  . modules.document_ocr.tasks.process_upload
celery@host ready.
```

**Terminal 4 — patient app**

```bash
cd frontend/patient_app
npm install
npm run dev -- --port 3000
```

**Terminal 5 — doctor portal**

```bash
cd frontend/doctor_portal
npm install
npm run dev -- --port 3001
```

## 10.3 Verify the whole path in 60 seconds

```bash
# 1. Log in as the demo patient
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"phone":"+919876543210","otp":"123456"}' | jq -r .access_token)

# 2. Upload a sample lab report
UPLOAD=$(curl -s -X POST http://localhost:8000/api/uploads \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@backend/03-document-ocr/tests/corpus/lab/cbc_clean_printed.jpg")
echo "$UPLOAD" | jq

UPLOAD_ID=$(echo "$UPLOAD" | jq -r .upload_id)

# 3. Poll until DONE
until [ "$(curl -s -H "Authorization: Bearer $TOKEN" \
     http://localhost:8000/api/uploads/$UPLOAD_ID | jq -r .status)" = "DONE" ]; do
  echo "processing…"; sleep 2
done

# 4. Read the summary
curl -s -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/uploads/$UPLOAD_ID/summary | jq
```

**Expected final output:**

```json
{
  "document_type": "lab_report",
  "paragraph": "Laboratory report with 8 test results extracted. 1 of 8 values falls outside the printed reference range. All values are as printed on the uploaded document. Clinical interpretation is for the treating physician.",
  "red_flags": [
    {
      "severity": "LOW",
      "test": "Haemoglobin",
      "value": 10.2,
      "unit": "g/dL",
      "range": "13.0–17.0",
      "message": "Haemoglobin: 10.2 g/dL — below the reference range (13.0–17.0)."
    }
  ],
  "counts": { "normal": 7, "abnormal": 1, "critical": 0, "unreadable": 0 },
  "safety_checked": true
}
```

If you see that JSON, the full path — upload → preprocess → hybrid OCR → parse → flag →
summarize → API — is working.

## 10.4 Common problems

| Symptom | Cause | Fix |
|---|---|---|
| `Unable to get page count` on PDF upload | poppler not on PATH | install `poppler-utils`; verify with `pdftoppm -v` |
| `ImportError: libGL.so.1` | missing OpenCV system libs | `apt-get install libgl1 libglib2.0-0` |
| First OCR request takes 2 minutes | models downloading at runtime | pre-download per §3.4/§3.5, or use the Docker image which bakes them in |
| Worker OOM-killed | TrOCR base + PaddleOCR in one process | drop `--concurrency` to 1, or use `trocr-small-handwritten` |
| "Show me the ink" shows the wrong region | bbox not mapped back through the transform | run `pytest tests/test_bbox_roundtrip.py` — this is the classic bug |
| `403` on the doctor's summary request | no active visit for that patient | create a visit, or check `assert_can_read_upload` |
| Uploads stuck in `QUEUED` | worker not running or wrong queue | check `celery … -Q ocr` is running and `CELERY_BROKER_URL` matches |
| Every prescription line abstains | formulary file empty or not found | check `lexicon/formulary.txt` exists and has content |

---

## Appendix — the three sentences to remember

> **1.** Knowing that it cannot read a line is a stronger and safer result than a confident
> wrong drug name.
>
> **2.** We read what the lab and the radiologist wrote. We never interpret the scan image, and
> we never diagnose.
>
> **3.** Every value shown to the doctor is a comparison against a printed reference range —
> a fact, not a conclusion.

# M4 — Document Intelligence (OCR & Clinical Extraction)

> **Owner:** Member 4
> **Read `00-INTRODUCTION.md` first.**
> **Service path:** `services/m4_document/`
> **Branch:** `m4-document`

---

## 1. Why this module exists

Every patient in an Indian OPD arrives carrying a plastic bag of paper: old prescriptions, lab slips, discharge summaries, imaging reports. The PS says it plainly — this paper is *"unstructured, often handwritten, in varying languages, and chronologically disordered,"* and reading it consumes a significant fraction of an already-scarce consultation.

M4 turns that bag of paper into **structured, dated, coded clinical facts** before the patient reaches the door.

### This is the hardest module in the project

Be honest about it. The PS itself concedes that handwritten Indian prescriptions are an exceptionally difficult OCR problem. Most teams will throw a generic OCR at a doctor's handwriting, get garbage, and demo the one prescription that happened to work.

**We take a different position, and it is USP #4:**

> **Do not free-decode. Constrain the vocabulary. And when confidence is low, refuse to guess.**

Two consequences:
1. The handwriting decoder is beam-restricted to India's real drug formulary — it is **physically incapable** of emitting a drug that does not exist.
2. Below a confidence floor, the system **abstains**: it crops the ink, shows it to the doctor, and says "I could not read this."

**Say this out loud in the pitch:** *knowing that it cannot read a line is a stronger and safer result than a confident wrong drug name.* Judges who understand medicine will immediately recognise this as the mature answer.

---

## 2. Responsibilities

| # | Responsibility | Detail |
|---|---|---|
| 1 | **Capture QC** | Reject blurry/glared/cropped shots *before* accepting them; guide the patient to re-shoot |
| 2 | **Image preprocessing** | Dewarp, deskew, denoise, shadow removal, binarisation |
| 3 | **Document classification** | Lab report / printed doc / prescription / imaging / ID card |
| 4 | **Printed OCR** | PaddleOCR, table-aware for lab reports |
| 5 | **Handwriting detection** | Decide which regions of a prescription are handwritten |
| 6 | **Handwriting OCR** | TrOCR with formulary-constrained decoding |
| 7 | **Clinical extraction** | NER + relation extraction: medicines, diagnoses, lab values, procedures |
| 8 | **Confidence layer** | High → auto-structure. Low → verify queue. |
| 9 | **Normalisation & coding** | Units, SNOMED CT, LOINC, ICD-11, NAMASTE |
| 10 | **Timeline construction** | Date resolution, chronological ordering, dedup of duplicate copies |
| 11 | **Abnormal-value flagging** | Out-of-range values, trends, drug-interaction pairs |
| 12 | **Provenance emission** | Every extracted entity carries its page + bounding box + crop |

### Explicitly NOT this module's job

- Interpreting what the values *mean* clinically (that is the doctor's job)
- Diagnosing anything from the documents
- Deciding what to show the doctor (M5 composes, M6 serves)

---

## 3. The pipeline

This is the team's agreed architecture, extended with capture QC, constrained decoding, provenance and the timeline stage.

```
                        Medical document
                              │
                              ▼
                  CAPTURE QC  (live, on-device)
                  blur score · glare / hotspot
                  corner detect · resolution check
                              │
                    ┌─────────┴─────────┐
                    ▼                   ▼
                  FAIL                 PASS
                    │                   │
                    ▼                   │
            guide the patient           │
            "थोड़ा बाईं ओर करें"          │
            "और रोशनी चाहिए"             │
            spoken via M2 TTS           │
                    │                   │
                    └──► re-shoot       │
                                        ▼
                              IMAGE PREPROCESSING
                              perspective dewarp
                              deskew
                              shadow removal
                              denoise
                              CLAHE contrast
                              adaptive binarise
                              (ORIGINAL kept forever)
                                        │
                                        ▼
                              DOCUMENT CLASSIFIER
                                        │
          ┌─────────────┬───────────────┼───────────┬─────────────┐
          ▼             ▼               ▼           ▼             ▼
     LAB REPORT    PRINTED DOC    PRESCRIPTION   IMAGING      ID CARD
                                                  REPORT          │
          │             │               │           │             ▼
          ▼             ▼               ▼           ▼        identity only
     PaddleOCR     PaddleOCR    HANDWRITING    PaddleOCR    no clinical
    table-aware:                 DETECTOR                    extraction
    preserve                  region-level:
    analyte ↔ value           which blocks are
    ↔ unit ↔ range            handwritten
          │             │               │
          │             │      ┌────────┴────────┐
          │             │      ▼                 ▼
          │             │  PaddleOCR          TrOCR
          │             │  printed parts:   handwritten
          │             │  letterhead,          │
          │             │  pre-printed          ▼
          │             │  field labels   CONSTRAINED DECODE
          │             │      │          beam limited to real
          │             │      │          formulary lexicon:
          │             │      │            generics · brands
          │             │      │            AYUSH formulations
          │             │      │            units · frequencies
          │             │      │            routes · durations
          │             │      │                  │
          │             │      │          model CANNOT emit
          │             │      │          a drug that does
          │             │      │          not exist
          │             │      │                  │
          │             │      └────────┬─────────┘
          └─────────────┴───────────────┘
                              │
                              ▼
              RAW OCR TEXT + BOUNDING BOXES
              every token: page · bbox
              · ocr_confidence · engine
                              │
                              ▼
                    CLINICAL EXTRACTION
                    NER + relation extraction
                              │
          ┌───────────────────┼───────────────────┐
          ▼                   ▼                   ▼
      MEDICINE            DIAGNOSIS           LAB VALUE
          │                   │                   │
          ▼                   ▼                   ▼
      name                 text                analyte
      strength             date                value
      unit                 ICD-11              unit
      frequency            NAMASTE             ref range
      duration                                 LOINC
      route                                    abnormal?
          │                   │                   │
          └───────────────────┼───────────────────┘
                              ▼
                      CONFIDENCE LAYER
              combined = ocr_conf × ner_conf
              × lexicon_match × context_plausibility
                              │
              ┌───────────────┴───────────────┐
              ▼                               ▼
      HIGH CONFIDENCE                  LOW CONFIDENCE
        ≥ 0.85                            < 0.60
              │                               │
              ▼                               ▼
      AUTO-STRUCTURE                  ⚠️  VERIFY QUEUE
      write DocEntity                 do NOT emit a value
      needs_verification              crop the ink region
        = false                       store crop blob
                                      needs_verification
                                        = true
                                              │
                                      doctor taps
                                      "show me the ink"
                                      sees real image
                                      types what it says
                                              │
                                      correction captured
                                      → OCR training pair
              │                               │
              └───────────────┬───────────────┘
                              ▼
                  NORMALISATION & CODING
                  unit conversion
                  drug name → generic
                  analyte → LOINC
                  diagnosis → ICD-11 / NAMASTE
                              │
                              ▼
                     TIMELINE BUILDER
                     date resolution
                       explicit > inferred > patient-stated
                       never invent a date
                     chronological ordering
                     DEDUP duplicate copies
                              │
                              ▼
                  ABNORMAL-VALUE FLAGGER
                              │
          ┌───────────────────┼───────────────────┐
          ▼                   ▼                   ▼
    out-of-range          trend across        drug-drug
    vs ref range          time points        interaction pairs
                        "HbA1c 9.2 → 8.6      states the fact
                         improving"           never advises
          │                   │                   │
          └───────────────────┼───────────────────┘
                              ▼
                    emits Alert(warning)
                              │
                              ▼
              DOC ENTITY SET + image_bbox provenance
                      + timeline
                              │
                              ▼
                           → M5
```

---

## 4. Component detail

### 4.1 Capture QC — the cheapest accuracy win

**Most OCR failures are capture failures.** A blurry photo cannot be fixed downstream. Catching it at capture, when the patient is still standing there with the paper in their hand, is worth more than any model improvement.

```python
def capture_qc(frame) -> QCResult:
    blur    = cv2.Laplacian(gray, cv2.CV_64F).var()      # < 100 → blurry
    glare   = fraction_of_pixels_above(gray, 250)         # > 0.05 → glare
    corners = detect_document_corners(frame)              # 4 corners visible?
    area    = corner_area / frame_area                    # > 0.35 → close enough
    skew    = estimate_skew(frame)                        # |skew| < 15°

    return QCResult(ok=..., reason=..., hint_key=...)
```

**Hints must be spoken, not just shown** (via M2 TTS):

| Failure | Hint (Hindi) |
|---|---|
| Blurry | "कागज़ को स्थिर रखें" (hold the paper still) |
| Glare | "थोड़ा घुमाएँ, चमक आ रही है" (turn it slightly, there is glare) |
| Corner missing | "पूरा कागज़ दिखाएँ" (show the whole paper) |
| Too far | "थोड़ा पास लाएँ" (bring it closer) |

**Best hardware setup:** a flat, lit scanner tray with a fixed overhead camera. Removes perspective distortion, controls lighting, and eliminates hand shake. If a tray is not available, a phone-style guided capture with a live overlay rectangle is the fallback.

### 4.2 Image preprocessing

Order matters.

```
1. Corner detection + perspective transform   → flat rectangle
2. Deskew                                     → text lines horizontal
3. Shadow removal                             → morphological background
                                                estimation, divide out
4. Denoise                                    → bilateral / non-local means
5. Contrast normalise (CLAHE)
6. Adaptive binarisation                      → for handwriting path only;
                                                keep greyscale for PaddleOCR
7. Upscale if DPI < 200                       → super-resolution optional
```

**Keep the original.** Every downstream crop for the verify queue must come from the *original* image, not the binarised one — the doctor needs to see the real ink, not a processed artefact.

### 4.3 Document classifier

Five classes. A small CNN or fine-tuned ViT on a few hundred labelled images is plenty.

| Class | Distinguishing features | Route to |
|---|---|---|
| `lab_report` | Tabular layout, reference-range column, lab letterhead | PaddleOCR table mode |
| `printed_doc` | Dense printed text, discharge summary format | PaddleOCR |
| `prescription` | Rx symbol, short lines, signature block, handwriting present | Handwriting detector |
| `imaging_report` | Radiology letterhead, "IMPRESSION:" section | PaddleOCR |
| `id_card` | ABHA/Aadhaar layout | Skip clinical extraction, use for identity only |

**Fallback:** if classification confidence is low, run **both** PaddleOCR and the handwriting detector, and merge. Cheap insurance.

### 4.4 Lab report path — table awareness

The critical requirement: **preserve the analyte ↔ value ↔ unit ↔ reference-range relation.** Naive line-by-line OCR destroys it and produces "HbA1c" and "9.2" as unrelated tokens.

```
PaddleOCR structure mode
      │
      ▼
detect table regions + cell grid
      │
      ▼
per row:  [ analyte | result | unit | reference range | flag ]
      │
      ▼
map columns by header matching (headers vary wildly between labs —
maintain a synonym list: "Result"/"Value"/"Observed", "Ref Range"/
"Normal Range"/"Biological Ref Interval")
      │
      ▼
emit one lab_value DocEntity per row, with the row's bbox
```

**Reference ranges may be absent.** Fall back to a built-in reference table keyed by analyte + sex + age. Flag which source was used.

### 4.5 Prescription path — handwriting

**Step 1 — region classification.** A prescription is rarely fully handwritten. The letterhead, the pre-printed field labels, the clinic address, sometimes the drug list, are printed. Only some regions are handwritten.

```
layout parse → text blocks
      │
      ▼
per block: handwritten? (small binary CNN on the block crop)
      │
   ┌──┴──┐
printed  handwritten
   │        │
PaddleOCR  TrOCR
```

**Step 2 — TrOCR with constrained decoding (USP #4).**

The insight: a doctor writing a prescription is not writing arbitrary English. They are writing from a **closed set** — drug names, dose numbers, standard frequency abbreviations, standard routes. Turning open-vocabulary recognition into closed-set recognition is a massive accuracy gain.

```
LEXICON (ontology/formulary.txt)
├── generic drug names          ~3,000
├── brand names (Indian market) ~12,000
├── AYUSH classical formulations ~1,500  ← don't forget these, AIIA cares
├── dose units                  mg, g, ml, IU, mcg, drops
├── frequencies                 OD, BD, TDS, QID, HS, SOS, PRN, STAT, Q6H
├── routes                      PO, IV, IM, SC, topical, per rectum
└── durations                   x3d, x5d, x1w, x1m, "for 10 days"

CONSTRAINED DECODE
    at each decoding step, mask the logits so only tokens that
    can continue a valid lexicon entry (or a number, or a
    recognised separator) have non-zero probability

    → the model CANNOT output "Metfromin" or "Xyzzyphen"
    → it outputs the nearest valid formulary entry, or it
      exhausts the beam and signals failure
```

**Implementation approaches, easiest first:**

| Approach | Effort | Quality |
|---|---|---|
| **A. Post-hoc lexicon snap** — free-decode, then fuzzy-match the output to the lexicon (edit distance + phonetic) | Low | Good. **Start here.** |
| **B. Beam re-ranking** — generate n-best beams, score each by lexicon membership, pick the best valid one | Medium | Better |
| **C. True constrained decoding** — trie-based logit masking during generation | High | Best |

**Ship A in Phase 2, upgrade to B in Phase 3, attempt C only if time remains.** Approach A alone already gives you the demo story and most of the accuracy.

**Step 3 — prescriber-specific adaptation (stretch).** The same doctor writes the same 20 drugs a hundred times a day. If the prescriber can be identified from the letterhead, weight the lexicon toward their historical prescribing pattern. Big accuracy win, easy to explain, very impressive if demoed.

### 4.6 Clinical extraction — NER + relations

Entities alone are useless. `Metformin`, `500`, `mg`, `BD` as four unlinked tokens tells the doctor nothing. **The relations are the value.**

```
TEXT: "Tab. Metformin 500mg 1-0-1 x 30 days"

NER:
  [DRUG: Metformin] [STRENGTH: 500] [UNIT: mg]
  [FREQ: 1-0-1] [DURATION: 30 days]

RELATION EXTRACTION:
  Metformin --has_strength--> 500 mg
  Metformin --has_frequency--> 1-0-1  (normalise → BD)
  Metformin --has_duration--> 30 days
  Metformin --has_form--> tablet

OUTPUT: one medicine DocEntity, fully populated
```

**Indian prescription notation to handle:**

| Notation | Meaning |
|---|---|
| `1-0-1` | morning-noon-night → BD |
| `1-1-1` | TDS |
| `0-0-1` | HS (at night) |
| `1/2` | half tablet |
| `x 5d`, `x5/7` | for 5 days |
| `Tab.` `Cap.` `Syp.` `Inj.` | dosage form |
| `SOS` | as needed |
| `↑` `↓` | increase / decrease dose |

Build a normaliser for these. They appear on essentially every Indian prescription and generic NER models do not know them.

**Model choice:** a biomedical transformer (BioBERT/PubMedBERT-class) fine-tuned on annotated Indian prescription text, with a relation head. If annotation time is short, a strong rule-based extractor over the constrained OCR output gets surprisingly far — the lexicon has already done most of the disambiguation work.

### 4.7 Confidence layer — and the abstention gate

**The combined confidence is a product, not an average.** A weak link anywhere should sink the whole entity.

```python
combined = (
    ocr_confidence          # from PaddleOCR / TrOCR
  * ner_confidence          # from the extractor
  * lexicon_match_score     # 1.0 exact, decays with edit distance
  * context_plausibility    # is this dose plausible for this drug?
)
```

**Context plausibility is a safety net worth building.** "Metformin 5000 mg" is 10× the normal dose. Either the OCR misread a digit, or it is a genuine prescribing error. **Either way the doctor must see it.** Maintain a dose-range table for the top ~200 drugs and flag anything outside it.

**Thresholds (tune on your validation set):**

| Range | Action |
|---|---|
| `≥ 0.85` | Auto-structure. `needs_verification = false`. |
| `0.60 – 0.85` | Auto-structure but `needs_verification = true`. Doctor sees a soft marker. |
| `< 0.60` | **Abstain.** Do not emit a value. Emit a `needs_verification` entity with the crop and no decoded text. |

**The abstention entity:**

```json
{
  "entity_id": "uuid",
  "entity_type": "medicine",
  "payload": { "name": null, "raw_ocr_guess": "Melformn 50?" },
  "confidence": 0.41,
  "needs_verification": true,
  "source": {
    "type": "image_bbox",
    "page": 2,
    "bbox": [180, 412, 520, 448],
    "crop_blob_id": "uuid"          ← the doctor sees THIS
  }
}
```

At the console the doctor sees: **"1 line could not be read — [Show me the ink]"**, taps it, sees the actual crop at full resolution, and types what it says. That correction is captured as a training pair (USP #9).

### 4.8 Timeline builder

**Date resolution.** Three sources, in priority order:
1. Explicit date printed on the document
2. Date inferred from context ("review after 2 weeks" on a dated prescription)
3. Patient-stated date during the interview ("this one is from last Diwali")

If no date can be resolved, place the document in an "undated" bucket and show it separately. **Never invent a date.**

**Deduplication.** Patients photograph the same report twice, or carry a photocopy and the original. Dedup by:
- perceptual image hash (near-identical scans)
- entity-set overlap (same analytes, same values, same date → same report)

Keep one, note "2 copies present".

**Output:**

```json
{
  "timeline": [
    { "date": "2024-11-03", "type": "prescription", "summary": "Metformin 500 BD started",
      "entity_ids": ["..."], "provenance": "prov_id" },
    { "date": "2025-01-14", "type": "lab", "summary": "HbA1c 9.2% (high)",
      "entity_ids": ["..."], "provenance": "prov_id" },
    { "date": "2025-06-20", "type": "lab", "summary": "HbA1c 8.6% (high, improving)",
      "entity_ids": ["..."], "provenance": "prov_id" }
  ],
  "undated": [ ... ]
}
```

### 4.9 Abnormal-value flagger

Three checks, each emitting an `Alert(warning)`:

**1. Out of reference range**
Compare value against the range on the report, or the built-in table. Flag with direction and magnitude.

**2. Trend across time points**
Same analyte at ≥2 dates → compute direction. "HbA1c 9.2 → 8.6, improving" is a far more useful line for a doctor than two isolated numbers. This is one of the highest-value, lowest-effort features in the whole project.

**3. Drug-drug interaction pairs**
A curated table of high-severity pairs (start with ~100 clinically important ones). Flag the pair, cite it, **do not recommend an action**. Guardian (M5) will block anything that reads as advice.

```json
{
  "kind": "interaction",
  "severity": "warning",
  "title": "Potential interaction",
  "detail": "Warfarin and Aspirin both present in current medications.",
  "evidence_refs": ["entity_id_1", "entity_id_2"]
}
```

Note the phrasing: it states a fact, it does not say "stop the aspirin." **That distinction is the whole safety posture of this project.**

---

## 5. API surface

```
POST   /api/v1/session/{id}/document/qc
       body  { frame_b64 }
       →     { ok: bool, reason, hint_key, hint_text_local }
       # fast, called on a live camera loop — must return < 150ms

POST   /api/v1/session/{id}/document
       body  { image_b64, page_hint? }
       →     { document_id, job_id, status: "queued" }
       # async — OCR takes seconds, must not block the kiosk

GET    /api/v1/session/{id}/document/{document_id}
       →     { status: "queued|processing|done|failed",
               document_type, entities: [DocEntity], page_count }

GET    /api/v1/session/{id}/entities
       →     [ DocEntity ]

GET    /api/v1/session/{id}/timeline
       →     { timeline: [...], undated: [...], duplicates_removed: 1 }

GET    /api/v1/session/{id}/verify-queue
       →     [ { entity_id, crop_url, raw_ocr_guess, confidence } ]

POST   /api/v1/entity/{entity_id}/verify
       body  { corrected_value, verified_by }
       →     { updated: true }    # also emits a training pair

GET    /api/v1/document/{document_id}/crop?bbox=x,y,w,h
       →     image                # for the "show me the ink" feature
```

**Async is mandatory.** OCR on a multi-page prescription takes 3–15 seconds. The kiosk must let the patient continue (or finish and walk away) while it runs. Use the Celery/RQ queue M6 provides.

---

## 6. Data model

```sql
CREATE TABLE documents (
    document_id     UUID PRIMARY KEY,
    session_id      UUID NOT NULL,
    document_type   TEXT,
    page_count      INT DEFAULT 1,
    original_blob   UUID NOT NULL,      -- MinIO ref, ORIGINAL image
    processed_blob  UUID,               -- preprocessed version
    qc_score        REAL,
    classifier_conf REAL,
    status          TEXT NOT NULL,      -- queued|processing|done|failed
    perceptual_hash TEXT,               -- for dedup
    duplicate_of    UUID REFERENCES documents,
    created_at      TIMESTAMPTZ DEFAULT now(),
    processed_at    TIMESTAMPTZ
);

CREATE TABLE doc_entities (
    entity_id          UUID PRIMARY KEY,
    session_id         UUID NOT NULL,
    document_id        UUID REFERENCES documents,
    entity_type        TEXT NOT NULL,   -- medicine|diagnosis|lab_value|procedure|vital
    payload            JSONB NOT NULL,
    event_date         DATE,
    date_source        TEXT,            -- explicit|inferred|patient|none
    confidence         REAL NOT NULL,
    ocr_confidence     REAL,
    ner_confidence     REAL,
    lexicon_match      REAL,
    needs_verification BOOLEAN DEFAULT false,
    verified_by        TEXT,
    verified_value     JSONB,
    ocr_engine         TEXT,            -- paddleocr|trocr
    raw_text           TEXT,
    page               INT,
    bbox               INT[],           -- [x, y, w, h]
    crop_blob          UUID,
    provenance_id      UUID,
    created_at         TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX ON doc_entities (session_id, entity_type);
CREATE INDEX ON doc_entities (session_id, needs_verification);

CREATE TABLE ocr_training_pairs (
    pair_id         UUID PRIMARY KEY,
    crop_blob       UUID NOT NULL,
    model_output    TEXT,
    corrected_value TEXT NOT NULL,
    corrected_by    TEXT NOT NULL,
    entity_type     TEXT,
    created_at      TIMESTAMPTZ DEFAULT now()
);
```

---

## 7. Dependencies

| Depends on | For what |
|---|---|
| **M6** | Async job queue, MinIO for images and crops, database, API gateway |
| **M2** | *Optional* — Bhashini printed-Indic OCR as an alternative to PaddleOCR for Indic scripts; also TTS for spoken capture hints |
| **M3** | Signal that the interview is complete and scanning may begin (though scanning can also run in parallel) |
| **ontology/formulary.txt** | The drug lexicon — the core asset of this module |

| Provides to | What |
|---|---|
| **M5** | `DocEntity` set + timeline + abnormal/interaction alerts |
| **M6** | Verify queue for the triage/doctor console |

---

## 8. Failure modes

| Failure | Required behaviour |
|---|---|
| Image too poor after 3 QC retries | Accept it anyway, mark `qc_score` low, let the whole document go to the verify queue. **Never refuse the patient's document.** |
| Classifier unsure | Run both printed and handwriting paths, merge results, keep the higher-confidence entities |
| OCR returns nothing | Emit a single `needs_verification` entity for the whole page with the full-page crop. Doctor sees the image. |
| TrOCR produces a drug not in lexicon | Should be impossible with constrained decode. If using approach A (post-hoc snap) and no match is within threshold → **abstain**, do not emit the raw guess as a value |
| Dose is implausible | Emit the entity, set `needs_verification = true`, emit `Alert(warning)` with the plausibility reason |
| No date resolvable | Place in `undated`. Never guess a date. |
| Duplicate documents | Dedup, note the count, keep the higher-quality scan |
| Job takes > 60 s | Time out, emit whatever entities completed, mark the rest for verification. Never leave the doctor with a spinner. |
| MinIO unavailable | Fail the upload with a clear kiosk message. Do not silently drop a document. |

---

## 9. Testing

**Build the test corpus first — this is the critical path for M4.**

You need real Indian medical documents. Sources:
- Team members' own family prescriptions and lab reports (with permission, anonymised)
- Public sample lab report formats
- Synthetically generated prescriptions written by hand by team members imitating doctor handwriting
- Any publicly available Indian handwritten prescription datasets

**Target: 100+ documents, spanning at least 5 prescription styles and 5 lab report formats.** Label them. This corpus is what lets you *measure* rather than guess.

**Unit**
- Preprocessing does not lose the original
- Bounding boxes are correct after dewarp/deskew (crop what you claim to crop)
- Notation normaliser handles `1-0-1`, `x5d`, `Tab.`, `SOS`, `1/2`
- Lexicon snap: "Melformin" → "Metformin", "Xqzzy" → abstain

**Accuracy metrics — report all four**

| Metric | Definition | Target |
|---|---|---|
| **Drug name accuracy** | Correct drug name / total drugs present | Report honestly |
| **Dose accuracy** | Correct strength+frequency / total | Report honestly |
| **Lab value accuracy** | Correct analyte+value+unit / total | Should be high — printed |
| **Abstention precision** | Of the entities we abstained on, what fraction were genuinely unreadable | **This is the USP metric — it should be high** |

**The number to quote in the pitch is not raw accuracy.** It is: *"On our test set we correctly extracted X% of medications, and of the remainder we correctly identified Y% as unreadable rather than guessing."* That framing is honest and it is stronger.

**Integration**
- Upload → async job → entities available at the polling endpoint
- Verify queue populated for low-confidence entities
- Crop endpoint returns the correct image region
- Timeline correctly orders 3 documents across 3 dates and dedups a duplicate

---

## 10. Build order

**Phase 1 (vertical slice)**
- [ ] Upload endpoint + async job wiring
- [ ] Basic preprocessing (dewarp, deskew)
- [ ] PaddleOCR on one printed lab report
- [ ] Rule-based extraction of analyte/value/unit
- [ ] `DocEntity` written with bbox

**Phase 2 (depth)**
- [ ] Capture QC with spoken hints
- [ ] Full preprocessing chain
- [ ] Document classifier, 5 classes
- [ ] Table-aware lab report parsing
- [ ] Handwriting region detector
- [ ] TrOCR integration
- [ ] Lexicon snap (approach A) with formulary
- [ ] Indian prescription notation normaliser
- [ ] Confidence layer + thresholds

**Phase 3 (differentiators)**
- [ ] **Abstention queue + crop storage + "show me the ink"** ← the USP
- [ ] Beam re-ranking (approach B)
- [ ] Timeline builder with dedup
- [ ] Abnormal-value flagger + trend detection
- [ ] Drug-interaction pair table
- [ ] Dose plausibility check
- [ ] Verification → training pair capture

---

## 11. Demo checklist — what M4 must show

1. **Hold up a genuinely awful handwritten prescription.** Not a clean one. The worst one you have.
2. **Two drugs decoded correctly** — point at the formulary constraint: *"The model cannot output a drug that does not exist in the Indian formulary. It is not free-guessing."*
3. **One line refused.** Show the message: *"1 line could not be read."* Then: *"Every other team's system would have confidently given the doctor a wrong drug name here. Ours says it does not know."* **This is the strongest 15 seconds in the whole demo.**
4. **Tap "Show me the ink"** — the actual crop appears at full resolution. The doctor reads it in one second.
5. **The timeline** — three documents across three dates, automatically ordered, with HbA1c 9.2 → 8.6 flagged as improving. Say: *"The patient carried this in a plastic bag. It took the system four seconds."*
6. **Show a duplicate being deduped** if you have one.

---

## 12. Notes and gotchas

- **Build the test corpus in week 1.** Everything else in this module is guesswork without it. This is the single highest-priority task for M4.
- **The formulary lexicon is your most valuable asset.** Spend real time assembling it: CDSCO published lists, Jan Aushadhi generic list, and AYUSH classical formulations (AIIA will notice if the last one is missing).
- **Start with approach A (post-hoc lexicon snap).** It is 20% of the effort for 70% of the benefit. Do not start with true constrained decoding and run out of time.
- **Keep the original image forever (within retention policy).** Every crop for the verify queue comes from it.
- **Bounding boxes must survive preprocessing.** If you dewarp and deskew, you must transform the bbox coordinates back to original-image space, or "show me the ink" shows the wrong region. This is a very easy bug to ship. Test it explicitly.
- **Async, always.** A 12-second synchronous OCR call will make the kiosk feel broken and will time out your gateway.
- **Never invent a date, never invent a dose, never invent a drug.** Abstention is always available and is always the correct fallback.
- **Frame abstention as a feature, loudly.** Left unexplained, judges may read "could not read" as failure. Explained, it reads as clinical safety engineering. The explanation is one sentence — make sure it is in the script.

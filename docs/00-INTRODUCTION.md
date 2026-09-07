# PURVA — Project Introduction & Master Architecture

> **Read this file first. Every team member reads this file completely before opening their own module file.**

| | |
|---|---|
| **Problem Statement** | SIH26047 — Patient Case-Taking Software |
| **Organisation** | All India Institute of Ayurveda (AIIA), Ministry of Ayush |
| **Category / Theme** | Software · Medtech / Biotech / Healthtech |
| **Project codename** | **PURVA** — *Pre-consultation Universal Record & Voice Assistant* |
| **Team size** | 6 members, 6 backend modules |
| **This document covers** | What we are building, why, how the pieces connect, who owns what, and the data contracts that let 6 people work in parallel without blocking each other |
| **Not covered here** | Frontend / UI-UX design (separate document, to be written later) |

---

## Table of Contents

1. [The Problem](#1-the-problem)
2. [Our Solution in One Page](#2-our-solution-in-one-page)
3. [Why PURVA — the 9 Differentiators](#3-why-purva--the-9-differentiators)
4. [Level 1 — System Context](#4-level-1--system-context)
5. [Level 2 — Module Map & Data Flow](#5-level-2--module-map--data-flow)
6. [Level 3 — Every Module's Internal Pipeline](#6-level-3--every-modules-internal-pipeline)
7. [End-to-End Walkthrough (a real patient session)](#7-end-to-end-walkthrough)
8. [Team Ownership — who builds what](#8-team-ownership)
9. [Shared Data Contracts](#9-shared-data-contracts) ← **most important section for parallel work**
10. [Repository Structure](#10-repository-structure)
11. [Technology Stack](#11-technology-stack)
12. [Integration Plan & Milestones](#12-integration-plan--milestones)
13. [Rules Every Module Must Obey](#13-rules-every-module-must-obey)
14. [Glossary](#14-glossary)
15. [Master Flowchart — the complete working project](#15-master-flowchart)

---

## 1. The Problem

### 1.1 What the Ministry actually wrote

Three problems, stated in the official PS document:

**Problem 1 — the clock.**
Indian tertiary government hospitals register **4,000–10,000 OPD patients per day**. Doctor-to-patient consultation time is **2–5 minutes** (BMJ Open 2017 placed India's average primary-care consultation at just over 2 minutes — among the shortest in the world). In that window the physician must elicit history, examine, review old records, diagnose, counsel, and prescribe.

A well-conducted history yields the correct diagnosis in **70–80% of cases**, before any examination or investigation. It is also the *first* thing that gets dropped when time runs out. Result: systematic under-elicitation, missed comorbidities, repeated questioning across visits, and diagnostic error.

**Problem 2 — the paper.**
Patients arrive carrying physical prescriptions, lab reports, discharge summaries and imaging films from multiple prior providers. Handwritten, multilingual, chronologically disordered. Reading this bag of paper consumes a large share of the same 2–5 minutes. **There is no mechanism to digitise and organise it before the patient reaches the consultation room.**

**Problem 3 — the AYUSH gap.**
Ayurvedic history-taking (Trividha, Ashtavidha, **Dashavidha Pariksha**) requires assessment of Prakriti (constitution), Vikriti (current imbalance), Agni (digestive capacity), Koshtha (bowel nature), Ahara-Vihara (diet and lifestyle), Nidana (causative factors) and Samprapti (pathogenesis). This is a far larger framework than allopathic intake. Capturing it manually inside an OPD slot is **arithmetically impossible**, so practitioners abbreviate the very assessment that defines personalised Ayurvedic care.

**And the systemic gap:**
ABDM (Ayushman Bharat Digital Mission) has built the national rails — ABHA IDs, Health Information Exchange, FHIR interoperability. But the **"first-mile" problem is unsolved**: nothing captures structured history and digitises documents *into* the ABDM ecosystem at the point of care.

### 1.2 Why existing things do not solve it

| Existing thing | Why it fails |
|---|---|
| Hospital registration systems | Capture only demographics + token number. Zero clinical content. |
| Health apps / tele-triage chatbots | Need a smartphone, literacy, data, and pre-visit enrolment. Excludes elderly, rural, low-literacy, first-visit patients — i.e. most of the OPD load. |
| Nurse-led history desks | Human-resource-limited. Do not scale to 5,000 patients/day. Reintroduce the same bottleneck. |
| Generic document scanners | Produce an image. Do not extract, structure, chronologise, or link to a health record. |

### 1.3 The one-line problem

> There is no patient-facing system that captures a complete, structured, multilingual clinical history **and** digitises the patient's existing paper records **before** the consultation begins — and pushes the result into ABDM.

---

## 2. Our Solution in One Page

**PURVA** is a kiosk-and-web platform installed in the OPD waiting area. A patient uses the time they are already spending in the queue to complete their own clinical history.

```
Patient gets token
        │
        ▼
Walks to PURVA kiosk  ──────► sits down, taps their language
        │
        ▼
Logs in with ABHA, hears the consent read aloud, says "yes"
        │
        ▼
Has a 4-6 minute CONVERSATION in their own language.
The system asks smart follow-up questions like a doctor would.
        │
        ▼
Places their old prescriptions and lab reports on the scanner.
The system READS them, extracts drugs and lab values, builds a timeline.
        │
        ▼
Hears a summary read back: "This is what I recorded. Is it correct?"
        │
        ▼
Gets token + room number. Walks to the doctor.
        │
        ▼
DOCTOR'S SCREEN ALREADY HAS THE FULL HISTORY.
Doctor reads it in 20 seconds, edits anything wrong, signs.
        │
        ▼
Doctor spends the entire 5 minutes on EXAMINATION and REASONING.
        │
        ▼
Record is pushed to the patient's ABHA account as a FHIR bundle.
```

**And if the patient is having a heart attack, PURVA stops the interview mid-question and moves them to the front of the queue.**

### The hard rule that shapes everything

> **PURVA elicits, structures and evidences. It NEVER diagnoses, NEVER suggests treatment, NEVER recommends a drug, and NEVER states a clinical fact it cannot point back to a source for.**

Every architectural decision in this document exists to make that rule *provable*, not just promised.

---

## 3. Why PURVA — the 9 Differentiators

Every other SIH team on this PS will build: speech-to-text + OCR + an LLM that writes a summary. That is the **baseline**, not the solution. These nine are our delta.

| # | Differentiator | What it means | Owned by |
|---|---|---|---|
| **1** | **Provenance-locked summary** | Every line in the doctor's summary carries a pointer — an audio timestamp or an image bounding box. Doctor taps a line and **hears the patient say it**. Any generated fact with no source pointer is **deleted before rendering**, not flagged. | M5 |
| **2** | **Guardian — safety as a second model** | A separate classifier inspects every output for diagnostic language, treatment advice, drug recommendation. Blocks and rewrites. We show judges a live counter: *"14,203 outputs · 61 blocked · 0 diagnostic statements emitted."* | M5 |
| **3** | **Live triage interrupt** | Red-flag detector runs **in parallel** with the interview, not after. On a hit the interview **aborts mid-question**, kiosk alarms, triage desk is pushed, queue token is re-sequenced to the front. The kiosk becomes a triage instrument, not a form. | M3 |
| **4** | **Formulary-constrained OCR with honest abstention** | Handwriting decoder is beam-restricted to India's real drug formulary — it is **physically incapable** of emitting a drug that does not exist. Below the confidence floor it **refuses**, crops the ink, and asks the doctor to read it. Knowing it cannot read is a stronger result than a confident wrong drug name. | M4 |
| **5** | **Dual-coded AYUSH record** | Scored Prakriti profile (Vata/Pitta/Kapha with confidence) from a validated instrument, coded in **NAMASTE** terminology and dual-mapped to **ICD-11 TM2**. One record readable by a vaidya *and* an allopathic consultant. | M5 |
| **6** | **Delta summary** | From visit 2 onward the doctor sees **only what changed**: "Pain 4/10, was 8/10. New: ankle oedema. Adherence ≈60%." Four lines instead of two pages. Time saved compounds every visit. | M5 |
| **7** | **Auditable spoken consent** | DPDP Act 2023 needs informed, granular, revocable consent. A non-reader cannot give it against a wall of text. PURVA **speaks** the consent, records the spoken assent with a timestamp and a hash of the exact consent version. | M1 |
| **8** | **Edge-first, sovereign, offline-capable** | Quantised models run on a ₹40k node inside the facility. Bhashini cloud when reachable, local models when not. Health data never leaves the building until a consented, signed FHIR bundle syncs. **Demo: pull the network cable on stage.** | M2 + M6 |
| **9** | **Physician-in-the-loop learning** | Every doctor correction is stored as a labelled training pair. Field accuracy is charted over time. *"71% in week 1 → 89% by week 6."* | M5 + M6 |

---

## 4. Level 1 — System Context

Zoomed all the way out. Five actors, one platform, three external systems.

```
                            PATIENT
                    speaks · taps · scans papers
                               │
                               ▼
                          PURVA KIOSK
                    mic · screen · camera · scanner
                               │
                               ▼
                        PURVA PLATFORM
                  M1 · M2 · M3 · M4 · M5 · M6
                               │
        ┌──────────┬───────────┼───────────┬──────────┐
        ▼          ▼           ▼           ▼          ▼
   PHYSICIAN    TRIAGE      ABHA /     HOSPITAL   BHASHINI
                 NURSE       ABDM         HIS
        │          │           │           │          │
        ▼          ▼           ▼           ▼          ▼
    summary   red-flag     FHIR R4     encounter   STT · NMT
   + timeline   queue      national      token      · TTS
   reads·edits  priority     PHR                   · OCR
    · signs      alert
```

**What goes IN:** patient voice (22 languages), touch selections, camera images of prior documents, ABHA identity.

**What comes OUT:** physician-ready structured summary, chronological timeline, FHIR R4 bundle to ABHA PHR, triage alert, patient-facing audio confirmation.

**What NEVER comes out:** a diagnosis. A treatment suggestion. A drug recommendation. An unsourced clinical claim. Any data without a consent artefact.

---

## 5. Level 2 — Module Map & Data Flow

Six modules. Each one is owned by exactly one team member.

```
                        PATIENT AT KIOSK
                               │
                               ▼
                   M1   IDENTITY & CONSENT
                          [Member 1]
                 ABHA login · language select
                 spoken consent · session create
                               │
                               │  session_id · language · consent_id
                               ▼
                   M2   LANGUAGE LAYER
                          [Member 2]
                 Bhashini STT · NMT · TTS
                 protected-term masking
                               │
                               │  English text
                               ▼
                   M3   CONVERSATION ENGINE
                          [Member 3]
                 adaptive questions · SOCRATES
                 ROS · Dashavidha · slot filling
                               │
              ┌────────────────┴────────────────┐
              ▼                                 ▼
         SLOT STORE                     ⚠ RED-FLAG HIT
      value · confidence                        │
      · audio_offset                            ▼
              │                          TRIAGE ALERT
              │                        queue re-sequence
              │                          nurse notified
              │
              │              M4   DOCUMENT OCR
              │                     [Member 4]
              │            preprocess · classify
              │            PaddleOCR / TrOCR
              │            extract · confidence gate
              │            timeline
              │                        │
              │                        │  doc entities · bboxes
              └───────────┬────────────┘
                          ▼
                   M5   FUSION & SAFETY
                          [Member 5]
                 conflict resolve · Prakriti
                 NAMASTE ↔ ICD-11 · schema-locked
                 PROVENANCE BINDER · 🛡 GUARDIAN
                 delta engine
                          │
                          │  summary · alerts · FHIR content
                          ▼
                   M6   PLATFORM CORE
                          [Member 6]
                 gateway · DB · queue · storage
                 triage svc · doctor svc · metrics
                 edge deploy · offline sync
                          │
        ┌─────────────┬───┴────┬─────────────┐
        ▼             ▼        ▼             ▼
     DOCTOR       TRIAGE    PATIENT       ADMIN
    CONSOLE        BOARD   DASHBOARD    DASHBOARD
```

### Cross-cutting layers (not a single module — rules everyone follows)

| Layer | What it is | Enforced by |
|---|---|---|
| **English interlingua** | All clinical logic operates on English. Bhashini only sits at the edges. Adding a 23rd language costs zero clinical engineering. | M2 provides, M3/M5 consume |
| **Provenance store** | Every clinical fact resolves to `audio_offset` or `image_bbox`. Written by M3 and M4, enforced by M5. | M5 gate |
| **Guardian** | No output leaves the system without passing the safety classifier. | M5 gate |
| **Consent gate** | No data is stored, processed, or transmitted without a valid consent artefact. | M1 gate |

---

## 6. Level 3 — Every Module's Internal Pipeline

Summary view only. **Full detail is in each module's own MD file.**

### M1 — Identity, Consent & ABDM

```
                    Patient at kiosk
                            │
                            ▼
                    Language select
                  (M2 TTS speaks options)
                            │
                            ▼
                    ABHA identity
                            │
          ┌─────────┬───────┼───────┬─────────┐
          ▼         ▼       ▼       ▼         ▼
       QR scan   14-digit  Aadhaar  New     FAILED
                  + OTP            patient    │
          │         │       │       │         ▼
          └─────────┴───┬───┴───────┘   local-only session
                        │                (no PHR push,
                        │                 intake continues)
                        ▼
                Consent text loaded
                  → SHA-256 hashed
                        │
                        ▼
                M2 TTS reads it aloud
                in patient's language
                        │
                        ▼
                Granular toggles
                        │
          ┌─────────┬───┴────┬──────────┐
          ▼         ▼        ▼          ▼
       capture   share    push to     retain
      (required)  w/ HIS    ABHA       audio
          │         │        │          │
          └─────────┴───┬────┴──────────┘
                        ▼
                Spoken assent recorded
              + timestamp + text hash
                        │
                        ▼
                CONSENT ARTEFACT
              revocable · auditable
                        │
                        ▼
                SESSION CREATED
            encrypted vault · TTL-bound
                        │
                        ▼
              M2 / M3 / M4 / M5 may now run
                        │
                        ▼
                  [session ends]
                        │
                        ▼
                FHIR R4 BUNDLE BUILT
                        │
                    network up?
                        │
              ┌─────────┴─────────┐
              ▼                   ▼
            YES                  NO
              │                   │
              ▼                   ▼
        ABDM HIP gateway    EDGE OUTBOX
        → patient PHR     store-and-forward
              │                   │
              │            sync on reconnect
              └─────────┬─────────┘
                        ▼
                SESSION VAULT PURGED
                 audit log written
```

### M2 — Language Layer (Bhashini)

```
        INBOUND — patient speaks              OUTBOUND — system speaks

              AUDIO IN                          ENGLISH TEXT IN
                 │                                    │
                 ▼                                    ▼
        VAD + noise suppression              PROTECTED-TERM MASK
                 │                                    │
                 ▼                                    ▼
          STORE AUDIO BLOB                  NMT → patient language
        (provenance anchor)                  Bhashini / local
                 │                                    │
                 ▼                                    ▼
              STT                                  UNMASK
        Bhashini / local                              │
        IndicConformer                                ▼
                 │                              TTS CACHE?
                 ▼                                    │
        Code-mix normaliser                 ┌─────────┴─────────┐
      "2 din se fever hai"                  ▼                   ▼
                 │                         HIT                 MISS
                 ▼                          │                   │
        PROTECTED-TERM MASK                 │                   ▼
        Metformin → ⟦D17⟧                   │                 TTS
        Vata      → ⟦A03⟧                   │         Bhashini / local
                 │                          │                   │
                 ▼                          └─────────┬─────────┘
          NMT → English                               ▼
                 │                                AUDIO OUT
                 ▼                              → kiosk speaker
              UNMASK
                 │
                 ▼
        ENGLISH TEXT OUT
          → M3 / M5
```

### M3 — Conversational History Engine

```
              English text from M2
              or touch event from kiosk
                        │
                        ▼
              SCHEMA-LOCKED SLOT FILLER
            LLM constrained to JSON grammar
              — cannot write free prose
                        │
          ┌─────────────┴─────────────┐
          ▼                           ▼
     SLOT STORE                ⚠ RED-FLAG ENGINE
   value · confidence          runs on EVERY utterance
   · audio_offset                       │
          │                   ┌─────────┴─────────┐
          │                   ▼                   ▼
          │              RULE ENGINE        ML CLASSIFIER
          │              deterministic       recall net
          │              (primary)          (never overrides)
          │                   │                   │
          │                   └─────────┬─────────┘
          │                             │
          │                   ┌─────────┴─────────┐
          │                   ▼                   ▼
          │               POSITIVE            NEGATIVE
          │                   │                   │
          │                   ▼                   │
          │            ABORT INTERVIEW            │
          │            alarm · triage push        │
          │            queue re-sequence          │
          │            partial slots kept         │
          │                                       │
          └───────────────────┬───────────────────┘
                              ▼
                     DIALOGUE MANAGER
              ontology-constrained state machine
                              │
        ┌──────────┬──────────┼──────────┬──────────┐
        ▼          ▼          ▼          ▼          ▼
     CHIEF     SOCRATES    SYSTEM      ROS       AYUSH
   COMPLAINT   S·O·C·R·    BRANCH     SWEEP     BRANCH
               A·T·E·S    cardiac              Prakriti
                          resp · GI            Agni
                          neuro · MSK          Koshtha
                                              Ahara-Vihara
        │          │          │          │          │
        └──────────┴─────┬────┴──────────┴──────────┘
                         ▼
              NEXT-QUESTION POLICY
            information-gain ranked
                         │
                         ▼
                  COMPLETE?
                         │
              ┌──────────┴──────────┐
              ▼                     ▼
             NO                    YES
              │                     │
              ▼                     ▼
      English question       hand off to M4
      → M2 translate+speak    then M5
              │
              └──────► loop
```

### M4 — Document Intelligence (OCR)

This is the pipeline the team already agreed on, extended with provenance and the confidence gate.

```
                    Medical document
                            │
                            ▼
                Image preprocessing
        (dewarp · deskew · denoise · shadow removal · capture QC)
                            │
                            ▼
                  Document classifier
                            │
          ┌─────────────────┼──────────────────┐
          ▼                 ▼                  ▼
     LAB REPORT        PRINTED DOC        PRESCRIPTION
          │                 │                  │
          ▼                 ▼                  ▼
     PaddleOCR         PaddleOCR       Handwriting detector
     (table-aware)                            │
          │                 │           ┌─────┴─────┐
          │                 │           ▼           ▼
          │                 │      PaddleOCR      TrOCR
          │                 │     (printed部分)  (handwritten)
          │                 │           │           │
          │                 │           │     ┌─────▼─────────────┐
          │                 │           │     │ CONSTRAINED DECODE│
          │                 │           │     │ beam limited to   │
          │                 │           │     │ real formulary    │
          │                 │           │     └─────┬─────────────┘
          │                 │           └─────┬─────┘
          └─────────────────┴─────────────────┘
                            │
                            ▼
              Raw OCR text + BOUNDING BOXES
                            │
                            ▼
                 Clinical extraction (NER + relations)
                            │
          ┌─────────────────┼─────────────────┐
          ▼                 ▼                 ▼
      MEDICINE          DIAGNOSIS         LAB VALUE
          │                 │                 │
          ▼                 ▼                 ▼
   dosage·frequency       date         value·unit·range
   ·duration·route                     ·analyte·LOINC
          │                 │                 │
          └─────────────────┼─────────────────┘
                            ▼
                    CONFIDENCE LAYER
                            │
                    ┌───────┴────────┐
                    ▼                ▼
            HIGH confidence     LOW confidence
                    │                │
                    ▼                ▼
            auto-structure    ⚠️ VERIFY QUEUE
                    │         (crop of the ink shown
                    │          to doctor at console)
                    └────────┬───────┘
                             ▼
                    TIMELINE BUILDER
                    (date resolution · dedup duplicates)
                             │
                             ▼
                    ABNORMAL-VALUE FLAGGER
                    (out-of-range · trend · interaction pairs)
                             │
                             ▼
                DOC ENTITY SET + image_bbox provenance
                             │
                             ▼
                          → M5
```

### M5 — Fusion, Summary & Safety

```
    SLOT STORE          DOC ENTITIES        PRIOR ENCOUNTERS
      from M3             from M4            from M1 / ABHA
         │                   │                     │
         └─────────┬─────────┴─────────────────────┘
                   ▼
            NORMALISE & ALIGN
         units · dates · drug generics
                   │
                   ▼
            CONFLICT RESOLVER
      patient says "no diabetes"
      but Rx shows Metformin
      → SURFACE BOTH · NEVER MERGE
                   │
         ┌─────────┴─────────┐
         ▼                   ▼
   PRAKRITI SCORER      DUAL CODING
   Vata / Pitta /      NAMASTE ↔ ICD-11 TM2
   Kapha + confidence   + SNOMED · LOINC
         │                   │
         └─────────┬─────────┘
                   ▼
      SCHEMA-CONSTRAINED GENERATOR
      fills a fixed clinical JSON
      — cannot emit free prose
                   │
                   ▼
         PROVENANCE BINDER
      every field must resolve to
      audio_offset OR image_bbox
                   │
         ┌─────────┴─────────┐
         ▼                   ▼
    NO SOURCE             SOURCED
         │                   │
         ▼                   │
    🗑 DISCARDED             │
    (logged, never          │
     rendered)              ▼
                     🛡 GUARDIAN
                  diagnosis? treatment?
                  drug recommendation?
                            │
                  ┌─────────┴─────────┐
                  ▼                   ▼
             VIOLATION              CLEAN
                  │                   │
                  ▼                   │
            BLOCK + rewrite           │
            + log + counter++         │
                                      ▼
                               DELTA ENGINE
                          diff vs last encounter
                          (return visits only)
                                      │
          ┌───────────────┬───────────┴───────────┐
          ▼               ▼                       ▼
   PHYSICIAN VIEW   PATIENT RECAP          FHIR CONTENT
      English        local language           → M1
   CC → HPI → PMH    audio via M2         Patient · Encounter
   → PSH → Drugs     "यह मैंने लिखा है,     · Condition
   → Allergy →        सही है?"             · Observation
   Family →                                · MedicationStatement
   Personal → ROS                          · DocumentReference
   → Investigations                        · Consent
   + AYUSH block
   + alerts
   + timeline
          │
          ▼
   doctor edits a field
          │
          ▼
   CORRECTION CAPTURED
   → accuracy metrics
   → training signal
```

### M6 — Platform Core & Clinical Services

```
              kiosk · doctor console · triage board
                      · patient dashboard
                               │
                               ▼
                    API GATEWAY (FastAPI)
              routing · auth · validation · tracing
                               │
                   ┌───────────┴───────────┐
                   ▼                       ▼
              SYNC PATH               ASYNC PATH
           budget 3 s / turn       budget 60 s / job
                   │                       │
           session · consent          OCR jobs (M4)
           turns (M3) · STT/TTS       FHIR push (M1)
           summary render (M5)        TTS pre-warm (M2)
                   │                  offline sync
                   │                       │
                   └───────────┬───────────┘
                               ▼
                          DATA LAYER
                               │
                ┌──────────────┼──────────────┐
                ▼              ▼              ▼
           PostgreSQL       Redis           MinIO
           sessions      session vault    audio blobs
           slots         (TTL, encrypted) doc images
           entities      job queue        crops
           summaries     cache            TTS cache
           provenance
           audit (append-only)
                               │
          ┌────────────┬───────┴───────┬────────────┐
          ▼            ▼               ▼            ▼
      TRIAGE       DOCTOR          METRICS       PATIENT
     SERVICE      SERVICE          SERVICE       SERVICE
   red-flag Q    summary fetch   Guardian ctr   own timeline
   re-sequence   field edit      field accuracy consent revoke
   nurse push    sign            latency p50/95
   verify queue  provenance      engine mix
                 replay
                               │
                               ▼
                        LLM RUNTIME
              one model server · two grammars
              M3 slot schema · M5 summary schema
                               │
                               ▼
                         EDGE NODE
              docker compose · models preloaded
              offline detect · store-and-forward
                    serves 4–8 kiosks
```

---

## 7. End-to-End Walkthrough

**A real session, step by step, with the module responsible at each step.**

| # | What happens | Module | Data produced |
|---|---|---|---|
| 1 | Patient collects OPD token, walks to kiosk | — | — |
| 2 | Kiosk shows language grid; each option spoken aloud in rotation | M1 + M2 | `language` |
| 3 | Patient taps हिन्दी | M1 | — |
| 4 | Patient scans ABHA QR (or speaks 14-digit + OTP, or Aadhaar, or registers new) | M1 | `abha_id`, patient demographics |
| 5 | Consent text (version-hashed) is **spoken aloud** in Hindi via TTS | M1 + M2 | `consent_text_hash` |
| 6 | Patient says "हाँ". Assent recorded with timestamp | M1 | `consent_artefact` |
| 7 | Session created in encrypted vault with TTL | M1 + M6 | `session_id` |
| 8 | System asks in Hindi: "आज आपको क्या तकलीफ़ है?" | M3 → M2 | — |
| 9 | Patient says "सीने में दर्द है, तीन दिन से" | M2 STT | raw transcript + `audio_offset` |
| 10 | Code-mix normalised, medical terms masked, translated to English | M2 | `"chest pain, 3 days"` |
| 11 | Slot filler writes `chief_complaint = chest pain`, `duration = 3 days` | M3 | 2 slots + provenance |
| 12 | **Red-flag engine scans the utterance in parallel** — no hit yet | M3 | — |
| 13 | Dialogue manager selects SOCRATES branch → next question is **R (Radiation)** | M3 | — |
| 14 | "दर्द कहाँ तक जाता है?" spoken + shown + tappable options | M3 → M2 | — |
| 15 | Patient: "बाएँ हाथ तक" + mentions sweating | M2 → M3 | slot `radiation = left arm` |
| 16 | **RED FLAG.** Rule `CARDIAC-01` fires: chest pain + left-arm radiation + diaphoresis | M3 | `alert(red_flag)` |
| 17 | Interview **aborts mid-question**. Kiosk alarms in Hindi: "कृपया यहीं रुकें।" | M3 | — |
| 18 | Triage board updates. Token 47 → position 1. Nurse pushed. | M6 | `queue_event` |
| 19 | *(Normal path continues for non-emergency patients)* ROS sweep + AYUSH branch: Agni, Koshtha, Ahara-Vihara | M3 | ~40 slots |
| 20 | "पुराने कागज़ यहाँ रखें" — patient places 3 documents on scanner tray | M4 | 3 images |
| 21 | Live capture QC: blur/glare check, "थोड़ा बाईं ओर करें", reshoot if bad | M4 | — |
| 22 | Preprocess → classify → 1 lab report, 2 prescriptions | M4 | doc types |
| 23 | Lab report → PaddleOCR (table-aware). Prescriptions → handwriting detector → TrOCR with **formulary-constrained decoding** | M4 | raw text + bboxes |
| 24 | Clinical extraction: `Metformin 500 BD`, `Telmisartan 40 OD`, `HbA1c 9.2%`, `HbA1c 8.6%` | M4 | doc entities |
| 25 | One handwritten line scores below confidence floor → **VERIFY queue**, crop retained | M4 | `abstention` |
| 26 | Timeline built, HbA1c flagged out-of-range and improving | M4 | timeline + flags |
| 27 | Fusion: slots + entities merged. Patient said "no diabetes" but Metformin present → **CONFLICT, both surfaced** | M5 | `alert(conflict)` |
| 28 | Prakriti scored: Vata 0.44 / Pitta 0.36 / Kapha 0.20, confidence 0.71. Coded NAMASTE + ICD-11 TM2 | M5 | ayush block |
| 29 | Schema-constrained generator fills the clinical JSON | M5 | draft summary |
| 30 | **Provenance binder**: 3 fields have no source → **discarded silently** | M5 | — |
| 31 | **Guardian** scans output. Clean. Counter incremented. | M5 | — |
| 32 | This is visit 3 → **delta engine** computes: pain 7/10 (was 8/10), new: chest pain | M5 | delta block |
| 33 | Patient hears recap in Hindi: "यह मैंने लिखा है…" and confirms | M5 → M2 | — |
| 34 | Kiosk shows Token 47, Room 3. Session vault purged. | M1 + M6 | — |
| 35 | Doctor's console lights up **before the patient reaches the door** | M6 | — |
| 36 | Doctor reads summary in ~20s. Taps a line → **hears the patient's own voice** | M6 + M5 | — |
| 37 | Doctor corrects one field. Correction stored as training pair. | M6 + M5 | `correction` |
| 38 | Doctor signs. FHIR R4 bundle built, signed, pushed to ABDM HIP gateway. | M1 | `fhir_bundle_id` |
| 39 | If offline: bundle queued on edge node, syncs when link returns | M6 | — |
| 40 | Patient later opens their dashboard, sees their own timeline + audio recap | M6 | — |

---

## 8. Team Ownership

| Member | Module | Code | Primary skill needed | Hardest part they own |
|---|---|---|---|---|
| **1** | Identity, Consent & ABDM/FHIR | **M1** | Backend, auth, standards | ABHA sandbox integration + FHIR R4 bundle correctness |
| **2** | Language Layer (Bhashini) | **M2** | API integration, audio, NLP | Protected-term masking + offline model fallback |
| **3** | Conversational History Engine | **M3** | NLP, LLM, clinical logic | Adaptive dialogue policy + red-flag engine |
| **4** | Document Intelligence (OCR) | **M4** | CV, OCR, ML | Handwriting decode + constrained vocabulary + confidence calibration |
| **5** | Fusion, Summary & Safety | **M5** | LLM, data modelling | Provenance binding + Guardian + Prakriti scoring |
| **6** | Platform Core & Clinical Services | **M6** | Backend, DevOps, DB | API contracts + async pipeline + edge deployment |

**Frontend** is a separate work-stream. UI/UX document will be written after this set. Whoever finishes their backend module first pairs onto frontend.

### Dependency graph — who blocks whom

```
M6 (platform)  ──► everyone      [BUILD FIRST — day 1 priority]
M2 (language)  ──► M1, M3, M5
M1 (identity)  ──► M3 (needs session), M5 (needs consent)
M3 (dialogue)  ──► M5
M4 (OCR)       ──► M5
M5 (fusion)    ──► M6 doctor services
```

**Rule:** M6 must ship the API skeleton + database schema + mock endpoints on **day 1**. Everyone else codes against mocks and swaps in real implementations. Nobody waits.

---

## 9. Shared Data Contracts

> **This is the most important section in this document. These objects are the interface between modules. Do not change one without telling the whole team.**

All contracts live in code at `purva/contracts/` as Pydantic models. This MD file and that code must stay in sync.

### 9.1 `Session`

```json
{
  "session_id": "uuid",
  "abha_id": "12-3456-7890-1234 | null",
  "patient_ref": "uuid | null",
  "language": "hi | ta | te | bn | mr | en | ...",
  "opd_type": "allopathic | ayush",
  "consent_id": "uuid",
  "token_number": 47,
  "state": "created | consented | interviewing | scanning | summarising | complete | aborted",
  "started_at": "iso8601",
  "expires_at": "iso8601",
  "is_return_visit": true,
  "previous_encounter_id": "uuid | null"
}
```

### 9.2 `Slot` — produced by M3, consumed by M5

```json
{
  "slot_id": "uuid",
  "session_id": "uuid",
  "ontology_key": "hpi.pain.radiation",
  "value": "left arm",
  "value_type": "string | number | boolean | enum | scale",
  "unit": "null | days | /10 | mg",
  "confidence": 0.92,
  "source": {
    "type": "audio | touch | inferred",
    "audio_offset_ms": [123400, 127800],
    "audio_blob_id": "uuid",
    "raw_transcript": "बाएँ हाथ तक",
    "translated": "up to the left arm"
  },
  "answered_by": "self | proxy",
  "framework": "socrates | ros | dashavidha | demographics | general",
  "created_at": "iso8601"
}
```

### 9.3 `DocEntity` — produced by M4, consumed by M5

```json
{
  "entity_id": "uuid",
  "session_id": "uuid",
  "document_id": "uuid",
  "document_type": "prescription | lab_report | discharge_summary | imaging | id_card",
  "entity_type": "medicine | diagnosis | lab_value | procedure | vital",
  "payload": {
    "// medicine": {
      "name": "Metformin",
      "normalised_name": "metformin",
      "strength": "500",
      "strength_unit": "mg",
      "frequency": "BD",
      "duration_days": 30,
      "route": "oral"
    },
    "// lab_value": {
      "analyte": "HbA1c",
      "loinc": "4548-4",
      "value": 9.2,
      "unit": "%",
      "ref_low": 4.0,
      "ref_high": 5.6,
      "is_abnormal": true
    },
    "// diagnosis": {
      "text": "Type 2 Diabetes Mellitus",
      "icd11": "5A11",
      "namaste": null
    }
  },
  "event_date": "2025-01-14 | null",
  "confidence": 0.88,
  "needs_verification": false,
  "source": {
    "type": "image_bbox",
    "page": 1,
    "bbox": [412, 88, 690, 118],
    "crop_blob_id": "uuid",
    "ocr_engine": "paddleocr | trocr",
    "raw_text": "Metformin 500mg BD"
  }
}
```

### 9.4 `Alert` — produced by M3/M4/M5, consumed by M6

```json
{
  "alert_id": "uuid",
  "session_id": "uuid",
  "kind": "red_flag | conflict | abnormal_value | unreadable | interaction",
  "severity": "critical | warning | info",
  "rule_id": "CARDIAC-01 | null",
  "title": "Exertional chest pain with left-arm radiation",
  "detail": "Patient reports radiation to left arm with diaphoresis.",
  "evidence_refs": ["slot_id", "entity_id"],
  "raised_by": "M3 | M4 | M5",
  "raised_at": "iso8601",
  "acknowledged_by": "user_id | null"
}
```

### 9.5 `ClinicalSummary` — produced by M5, consumed by M6/frontend

```json
{
  "summary_id": "uuid",
  "session_id": "uuid",
  "status": "draft | edited | signed",
  "sections": {
    "chief_complaint": [{ "text": "Chest pain, 3 days", "provenance": "prov_id" }],
    "hpi":             [{ "text": "...", "provenance": "prov_id" }],
    "past_medical":    [],
    "past_surgical":   [],
    "drugs":           [],
    "allergies":       [],
    "family_history":  [],
    "personal_history":[],
    "ros":             [],
    "investigations":  []
  },
  "ayush": {
    "prakriti": { "vata": 0.44, "pitta": 0.36, "kapha": 0.20, "confidence": 0.71 },
    "vikriti": "...",
    "agni": "vishamagni",
    "koshtha": "krura",
    "ahara_vihara": ["irregular meal timing", "night shift work"],
    "codes": { "namaste": "AAE-16", "icd11_tm2": "SF7Y" }
  },
  "timeline": [
    { "date": "2024-11", "type": "prescription", "text": "Metformin started", "provenance": "prov_id" }
  ],
  "delta": {
    "is_return_visit": true,
    "visit_number": 3,
    "changed": ["pain 7/10 (was 8/10)", "new: chest pain"],
    "adherence_estimate": 0.6
  },
  "alerts": ["alert_id"],
  "guardian": { "checked": true, "blocked_count": 0, "version": "g-1.2" },
  "generated_at": "iso8601"
}
```

### 9.6 `Provenance` — written by M3 & M4, enforced by M5

```json
{
  "prov_id": "uuid",
  "session_id": "uuid",
  "kind": "audio_offset | image_bbox | physician_entry",
  "audio": { "blob_id": "uuid", "start_ms": 123400, "end_ms": 127800 },
  "image": { "blob_id": "uuid", "page": 1, "bbox": [412, 88, 690, 118] },
  "created_by": "M3 | M4 | physician"
}
```

**Hard rule:** M5 renders a field **only if** it resolves to a valid `prov_id`. No exceptions, no "flag it and show it anyway."

### 9.7 Internal API contract (M6 owns, everyone consumes)

```
POST   /api/v1/session                       → create session          [M1]
POST   /api/v1/session/{id}/consent          → record consent          [M1]
POST   /api/v1/lang/stt                      → audio → English text    [M2]
POST   /api/v1/lang/tts                      → English text → audio    [M2]
POST   /api/v1/session/{id}/turn             → submit answer, get next [M3]
POST   /api/v1/session/{id}/document         → upload doc (async job)  [M4]
GET    /api/v1/session/{id}/document/{did}   → job status + entities   [M4]
POST   /api/v1/session/{id}/summarise        → build summary           [M5]
GET    /api/v1/session/{id}/summary          → fetch summary           [M5]
PATCH  /api/v1/summary/{id}/field            → doctor edit             [M6]
POST   /api/v1/summary/{id}/sign             → sign + trigger FHIR     [M1]
GET    /api/v1/triage/queue                  → live triage board       [M6]
GET    /api/v1/patient/{abha}/timeline       → patient dashboard       [M6]
GET    /api/v1/admin/metrics                 → Guardian + accuracy     [M6]
```

---

## 10. Repository Structure

```
purva/
├── docs/
│   ├── 00-INTRODUCTION.md              ← this file
│   ├── 01-M1-identity-consent-abdm.md
│   ├── 02-M2-language-bhashini.md
│   ├── 03-M3-conversation-engine.md
│   ├── 04-M4-document-ocr.md
│   ├── 05-M5-fusion-summary-safety.md
│   ├── 06-M6-platform-core.md
│   └── 07-FRONTEND-UIUX.md             ← to be written later
│
├── contracts/                          ← M6 owns, everyone imports
│   ├── session.py
│   ├── slot.py
│   ├── doc_entity.py
│   ├── alert.py
│   ├── summary.py
│   └── provenance.py
│
├── services/
│   ├── m1_identity/
│   ├── m2_language/
│   ├── m3_conversation/
│   ├── m4_document/
│   ├── m5_fusion/
│   └── m6_platform/
│
├── ontology/                           ← shared clinical knowledge
│   ├── socrates.yaml
│   ├── ros.yaml
│   ├── dashavidha.yaml
│   ├── red_flags.yaml
│   ├── formulary.txt                   ← drug lexicon for M4
│   └── namaste_icd11_map.csv
│
├── models/                             ← downloaded / fine-tuned weights
├── frontend/
│   ├── kiosk/
│   ├── doctor-console/
│   ├── triage-board/
│   └── patient-dashboard/
├── infra/
│   ├── docker-compose.yml
│   └── edge/
└── tests/
```

**Branch rule:** one branch per module — `m1-identity`, `m2-language`, … Merge to `dev` only when the module's contract tests pass. `main` is demo-ready at all times.

---

## 11. Technology Stack

| Layer | Choice | Reason |
|---|---|---|
| **Speech to text** | Bhashini STT (ULCA pipeline API) · fallback quantised IndicConformer / IndicWhisper | Government platform = sovereignty + zero licence cost; local fallback keeps PHC working offline |
| **Translation** | Bhashini NMT · IndicTrans2 local | Interlingua bridge; protected-term masking wraps it |
| **Text to speech** | Bhashini TTS · Indic-TTS local | Required for consent read-aloud and non-readers |
| **Printed OCR** | **PaddleOCR** (Indic + Latin, table-aware) | Strong on printed Indic; table structure preserved for lab reports |
| **Handwriting OCR** | **TrOCR** fine-tuned on Indian prescription corpus, **beam-constrained to formulary** | Turns open-vocabulary into closed-set — highest-leverage decision in M4 |
| **Image preprocessing** | OpenCV — dewarp, deskew, denoise, shadow removal | Cheap accuracy gains before any model runs |
| **Dialogue / slot filling** | Small open instruct model, 4-bit, **JSON-grammar constrained decoding** (llama.cpp GBNF / vLLM guided decoding / Outlines) | Grammar is the safety mechanism — model cannot emit prose, only fill a schema |
| **Red-flag detection** | Deterministic rule engine (primary) + light classifier (recall net) | Rules are auditable and explainable to a clinician |
| **Guardian** | Fine-tuned small classifier, 3 labels: `diagnostic` / `therapeutic` / `clean` | Independent of the generator — a jailbroken generator still cannot ship a diagnosis |
| **Clinical NER** | Biomedical transformer + relation head → SNOMED CT, LOINC, ICD-11, NAMASTE | Coding is what makes the record interoperable, not merely digital |
| **Backend** | Python 3.11 · FastAPI · Pydantic v2 | Fast, typed, contract-first |
| **Database** | PostgreSQL 16 + SQLAlchemy + Alembic | Relational, auditable, JSONB where useful |
| **Cache / vault** | Redis (TTL-bound session vault) | Ephemeral by design — supports the "purge on submit" requirement |
| **Queue** | Celery or RQ | OCR and FHIR push are async; conversation is sync |
| **Object storage** | MinIO (S3-compatible), encrypted at rest | Audio blobs + document images + crops |
| **Interop** | HAPI FHIR server · ABDM HIP sandbox · HL7 v2 adapter | Most government HIS installs are not FHIR-native — the adapter is not optional |
| **Frontend** | React (PWA kiosk, offline-first) + React consoles | Three different users → three purpose-built surfaces |
| **Edge node** | Mini-PC or Jetson-class, ~₹40k, one per facility | Serves 4–8 kiosks; keeps audio inside the building |
| **Observability** | Structured logs + Prometheus-style counters | Guardian counter and latency per stage are demo assets |

---

## 12. Integration Plan & Milestones

### Phase 0 — Day 1 (everyone, together)

- [ ] M6 ships repo skeleton, `contracts/` Pydantic models, DB schema, docker-compose
- [ ] M6 ships **mock endpoints** for every API in §9.7 returning fixture data
- [ ] Everyone can run `docker compose up` and hit every endpoint
- [ ] Ontology files (`socrates.yaml`, `red_flags.yaml`, `dashavidha.yaml`) stubbed with 10 entries each

**Nobody is blocked after Phase 0. Everyone codes against mocks.**

### Phase 1 — Vertical slice (get one path working end to end)

- [ ] M1: ABHA mock login + consent recorded
- [ ] M2: Bhashini STT + TTS working for Hindi, hardcoded pipeline
- [ ] M3: 5-question fixed interview, slots written
- [ ] M4: PaddleOCR on one printed lab report, entities written
- [ ] M5: dumb summary that concatenates slots + entities
- [ ] M6: doctor console API returns the summary

**Success test:** one patient, one language, one document, summary appears on doctor endpoint.

### Phase 2 — Depth

- [ ] M2: NMT + protected-term masking + code-mix normaliser
- [ ] M3: adaptive SOCRATES branching + red-flag engine + AYUSH branch
- [ ] M4: handwriting path + TrOCR + constrained decode + confidence gate + timeline
- [ ] M5: provenance binder + Guardian + conflict resolver + Prakriti scorer
- [ ] M1: real FHIR bundle + ABDM sandbox push
- [ ] M6: triage service + async OCR queue + metrics

### Phase 3 — The differentiators (this is what wins)

- [ ] Tap-a-line-hear-the-audio (M5 + M6 + frontend)
- [ ] Red-flag interrupt with live queue re-sequencing (M3 + M6)
- [ ] Abstention queue — "show me the ink" (M4 + M6)
- [ ] Guardian live counter dashboard (M5 + M6)
- [ ] Offline failover — pull the cable and keep working (M2 + M6)
- [ ] Delta summary for return visits (M5)

### Phase 4 — Demo hardening

- [ ] Seed 3 realistic patient scenarios (normal / red-flag / return visit)
- [ ] Rehearse the 8-minute demo run order
- [ ] Failure drills: no network, bad scan, ASR mishears, LLM tries to diagnose

---

## 13. Rules Every Module Must Obey

1. **Never diagnose.** No module emits a disease name it was not explicitly told, a treatment, or a drug recommendation. M5's Guardian is the last gate, but every module is responsible upstream.
2. **Never state a fact without a source.** If you produce a clinical value, you produce a `provenance` record with it. M5 will silently discard anything unsourced.
3. **Never merge conflicting information.** Patient says X, document says not-X → surface both, flag it, let the doctor decide.
4. **Never block on the patient.** Any question can be skipped. A partial history is still valuable. The session must always be able to end.
5. **English in the middle.** All clinical logic in English. Language handling only at the edges, only in M2.
6. **Consent gates everything.** No processing, no storage, no transmission before a valid consent artefact exists.
7. **Ephemeral by default.** Raw audio and images are deleted after the session unless the patient consented to retention.
8. **Contract changes are announced.** Changing anything in §9 requires a message to the whole team and a version bump.
9. **Degrade, do not crash.** Bhashini down → local models. OCR fails → abstention queue. LLM fails → show raw slots. The kiosk must never show a stack trace to a patient.
10. **Latency is a feature.** A turn (patient speaks → next question spoken) must complete in under ~3 seconds, or the queue backs up and the whole premise collapses.

---

## 14. Glossary

| Term | Meaning |
|---|---|
| **ABDM** | Ayushman Bharat Digital Mission — India's national digital health infrastructure |
| **ABHA** | Ayushman Bharat Health Account — 14-digit national health ID |
| **AYUSH** | Ayurveda, Yoga, Unani, Siddha, Homeopathy — India's traditional medicine systems |
| **Agni** | Ayurvedic concept of digestive/metabolic fire; assessed as part of Dashavidha |
| **Ahara-Vihara** | Diet and lifestyle assessment |
| **ASR / STT** | Automatic Speech Recognition / Speech To Text |
| **Bhashini** | India's national language AI platform (MeitY) — STT, NMT, TTS, OCR for 22 languages |
| **Dashavidha Pariksha** | Ten-fold Ayurvedic patient examination |
| **DPDP Act 2023** | Digital Personal Data Protection Act — India's data privacy law |
| **FHIR** | HL7 Fast Healthcare Interoperability Resources — the health data exchange standard |
| **Guardian** | Our safety classifier that blocks diagnostic/therapeutic language |
| **HIP** | Health Information Provider — the ABDM role a hospital plays when pushing records |
| **HIS** | Hospital Information System |
| **HPI** | History of Present Illness |
| **ICD-11 TM2** | WHO disease classification, Traditional Medicine Module 2 |
| **Koshtha** | Ayurvedic assessment of bowel nature |
| **LOINC** | Standard codes for lab tests and observations |
| **NAMASTE** | National AYUSH Morbidity and Standardized Terminologies Electronic portal — India's AYUSH terminology codes |
| **NMT** | Neural Machine Translation |
| **OPD** | Out-Patient Department |
| **Prakriti** | Ayurvedic body constitution — Vata / Pitta / Kapha |
| **Provenance** | The pointer from a clinical fact back to its source (audio timestamp or image region) |
| **ROS** | Review of Systems — a systematic symptom sweep |
| **SNOMED CT** | International clinical terminology |
| **SOCRATES** | Pain history framework: Site, Onset, Character, Radiation, Associations, Time course, Exacerbating/relieving, Severity |
| **TTS** | Text To Speech |
| **ULCA** | Universal Language Contribution API — Bhashini's API layer |
| **Vikriti** | Ayurvedic current state of imbalance (vs Prakriti, the baseline) |

---

## 15. Master Flowchart

**The complete working project, one diagram.** This is the picture the whole team should carry in their head.

```
                    P U R V A  —  COMPLETE SYSTEM
                          end to end


                    Patient gets OPD token
                              │
                              ▼
              ① LANGUAGE GRID                        [M1 + M2]
              spoken aloud in rotation
                              │
                              ▼
              ② ABHA LOGIN                                [M1]
                              │
              ┌─────────┬─────┼─────┬─────────┐
              ▼         ▼     ▼     ▼         ▼
           QR scan  14-digit Aadhaar New    FAILED
                     + OTP          patient    │
              │         │     │       │        ▼
              └─────────┴──┬──┴───────┘  local-only session
                           │             (intake continues)
                           ▼
              ③ SPOKEN CONSENT                      [M1 + M2]
              TTS reads it · assent recorded · hashed
              granular: capture / share HIS /
                        push PHR / retain audio
                           │
                           ▼
              SESSION CREATED — encrypted vault, TTL   [M6]
                           │
                           ▼
       ═══════════════════════════════════════════════════
              ④ CONVERSATION LOOP                  [M2 + M3]
       ═══════════════════════════════════════════════════
                           │
                    patient speaks
                           │
                           ▼
                    Bhashini STT
                           │
                           ▼
                 code-mix normalise
                           │
                           ▼
                 MASK medical terms
                           │
                           ▼
                   NMT → English
                           │
              ┌────────────┴────────────┐
              ▼                         ▼
        SLOT FILLER            ⚠ RED-FLAG ENGINE
      JSON-grammar locked      rules + classifier
              │                         │
              ▼               ┌─────────┴─────────┐
        SLOT STORE            ▼                   ▼
      value · confidence   POSITIVE            NEGATIVE
      · audio_offset          │                   │
              │               ▼                   │
              │        ABORT + ALARM              │
              │        triage push                │
              │        queue jump                 │
              │        partial slots kept         │
              │                                   │
              └───────────────┬───────────────────┘
                              ▼
                     DIALOGUE MANAGER
                              │
        ┌──────────┬──────────┼──────────┬──────────┐
        ▼          ▼          ▼          ▼          ▼
     CHIEF     SOCRATES    SYSTEM      ROS       AYUSH
   COMPLAINT              BRANCH      SWEEP     BRANCH
                                               Prakriti
                                               Agni
                                               Koshtha
                                               Ahara-Vihara
        │          │          │          │          │
        └──────────┴─────┬────┴──────────┴──────────┘
                         ▼
                   next question
                         │
                         ▼
                NMT → local · UNMASK
                         │
                         ▼
                  Bhashini TTS
                         │
                         ▼
                 patient hears it
                         │
                         └──────► loop until complete
                              │
                              ▼
       ═══════════════════════════════════════════════════
              ⑤ DOCUMENT PIPELINE                      [M4]
       ═══════════════════════════════════════════════════
                              │
                    Patient places papers
                              │
                              ▼
                       CAPTURE QC
                    blur · glare · crop
                              │
                    ┌─────────┴─────────┐
                    ▼                   ▼
                  FAIL                 PASS
                    │                   │
              re-shoot with             ▼
              spoken hint         PREPROCESSING
                    │             dewarp · deskew
                    └──► back     denoise · shadow
                                        │
                                        ▼
                              DOCUMENT CLASSIFIER
                                        │
                    ┌───────────────────┼───────────────────┐
                    ▼                   ▼                   ▼
               LAB REPORT          PRINTED DOC        PRESCRIPTION
                    │                   │                   │
                    ▼                   ▼                   ▼
               PaddleOCR           PaddleOCR        HANDWRITING
              (table-aware)                          DETECTOR
                    │                   │                   │
                    │                   │         ┌─────────┴─────────┐
                    │                   │         ▼                   ▼
                    │                   │    PaddleOCR             TrOCR
                    │                   │   (printed parts)     (handwritten)
                    │                   │         │                   │
                    │                   │         │                   ▼
                    │                   │         │           CONSTRAINED
                    │                   │         │             DECODE
                    │                   │         │        real formulary only
                    │                   │         │                   │
                    │                   │         └─────────┬─────────┘
                    └───────────────────┴───────────────────┘
                                        ▼
                          RAW OCR TEXT + BOUNDING BOXES
                                        ▼
                            CLINICAL EXTRACTION
                             NER + relations
                                        │
                    ┌───────────────────┼───────────────────┐
                    ▼                   ▼                   ▼
                MEDICINE            DIAGNOSIS           LAB VALUE
                    │                   │                   │
                    ▼                   ▼                   ▼
             dose · frequency        date            analyte · value
             duration · route     ICD-11 · NAMASTE   unit · range · LOINC
                    │                   │                   │
                    └───────────────────┼───────────────────┘
                                        ▼
                              CONFIDENCE LAYER
                                        │
                            ┌───────────┴───────────┐
                            ▼                       ▼
                    HIGH confidence           LOW confidence
                            │                       │
                            ▼                       ▼
                    auto-structure           ⚠ VERIFY QUEUE
                                             crop of ink kept
                                             doctor confirms
                            │                       │
                            └───────────┬───────────┘
                                        ▼
                              TIMELINE BUILDER
                            date resolve · dedup
                                        ▼
                            ABNORMAL FLAGGER
                        out-of-range · trend · interaction
                                        │
                                        ▼
       ═══════════════════════════════════════════════════
              ⑥ FUSION, SUMMARY & SAFETY                [M5]
       ═══════════════════════════════════════════════════
                                        │
              slots + entities + prior ABHA encounters
                                        ▼
                            CONFLICT RESOLVER
                        surface both · never merge
                                        │
                            ┌───────────┴───────────┐
                            ▼                       ▼
                     PRAKRITI SCORER          DUAL CODING
                     Vata/Pitta/Kapha      NAMASTE ↔ ICD-11 TM2
                            │                       │
                            └───────────┬───────────┘
                                        ▼
                      SCHEMA-CONSTRAINED GENERATOR
                          fixed clinical JSON
                                        ▼
                            PROVENANCE BINDER
                                        │
                            ┌───────────┴───────────┐
                            ▼                       ▼
                        NO SOURCE               SOURCED
                            │                       │
                            ▼                       ▼
                       🗑 DISCARDED            🛡 GUARDIAN
                                                    │
                                        ┌───────────┴───────────┐
                                        ▼                       ▼
                                   VIOLATION                 CLEAN
                                        │                       │
                                        ▼                       ▼
                              BLOCK + log + count        DELTA ENGINE
                                                      visit 2+: what changed
                                                          + adherence
                                                                │
        ┌──────────────┬──────────────┬──────────────┬──────────┘
        ▼              ▼              ▼              ▼
   ⑦ PATIENT      ⑧ PHYSICIAN    ⑨ TRIAGE       ⑩ PATIENT
   AUDIO RECAP      CONSOLE         BOARD         DASHBOARD
   [M2 + M5]        [M5 + M6]        [M6]            [M6]
        │              │              │              │
        ▼              ▼              ▼              ▼
  "यह मैंने लिखा   Panel 1 Summary  red-flag Q    own timeline
   है, सही है?"    Panel 2 Alerts   + rule + time  lab trends
   local language  Panel 3 Timeline + verify queue audio recap
                   Panel 4 AYUSH                   consent revoke
                       │
                       ▼
             tap a line → HEAR PATIENT
             tap a box  → SEE THE INK
                       │
                       ▼
             doctor edits + signs
                       │
                       ▼
             CORRECTION CAPTURED
             → training pair → metrics
                       │
                       ▼
       ═══════════════════════════════════════════════════
              ⑪ FHIR R4 BUNDLE + PUSH                   [M1]
       ═══════════════════════════════════════════════════
                       │
              Patient · Encounter · Condition
              Observation · MedicationStatement
              DocumentReference · Consent
                       │
                   network up?
                       │
           ┌───────────┴───────────┐
           ▼                       ▼
          YES                     NO
           │                       │
           ▼                       ▼
    ABDM HIP gateway         EDGE OUTBOX
           │                store-and-forward
           ▼                       │
    patient's ABHA PHR      sync on reconnect
           │                       │
           └───────────┬───────────┘
                       ▼
              ⑫ SESSION VAULT PURGED             [M1 + M6]
                 audit log written
```

---

## Next steps for each member

1. Read this file end to end. Twice.
2. Open your own module file (`0X-MX-*.md`).
3. Read §9 Shared Data Contracts again — that is your interface with everyone else.
4. Wait for M6's Phase 0 skeleton (day 1), then start against mocks.
5. Any question that affects another module → ask in the group, not in DMs. Contract drift is the number one way a 6-person hackathon project dies.

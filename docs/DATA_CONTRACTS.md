# DATA CONTRACTS — PURVA

**The single source of truth for every JSON interface between modules.**
**Every engineer follows this exactly. No deviations. Changing anything here requires a message to the whole team and a `CONTRACT_VERSION` bump.**

Code lives in `contracts/` as Pydantic v2 models. This file and that code must stay in sync.

`CONTRACT_VERSION = 1.0.0`

---

## 0. Who produces what

| Object | Produced by | Consumed by |
|---|---|---|
| `Session` | M1 | everyone |
| `Consent` | M1 | M2 (audio retention), M5 (provenance mode), M6 |
| `Slot` | M3 | M5 |
| `DocEntity` | M4 | M5 |
| `Provenance` | M3, M4, physician | M5 (enforces), M6 (serves) |
| `Alert` | M3, M4, M5 | M6 |
| `ClinicalSummary` | M5 | M1 (FHIR), M6 (console), frontend |
| `Correction` | M6 (doctor edit) | M5, M3, M4 |

---

## 1. Session

```json
{
  "session_id": "uuid",
  "abha_id": "12-3456-7890-1234 | null",
  "patient_ref": "uuid | null",
  "language": "hi",
  "opd_type": "allopathic | ayush",
  "consent_id": "uuid",
  "token_number": 47,
  "kiosk_id": "AIIA-OPD-K03",
  "state": "created | consented | interviewing | scanning | summarising | complete | aborted",
  "phr_linked": true,
  "is_return_visit": true,
  "previous_encounter_id": "uuid | null",
  "started_at": "2026-09-03T14:22:07+05:30",
  "expires_at": "2026-09-03T16:22:07+05:30"
}
```

**Language codes:** ISO 639-1 — `hi ta te bn mr gu kn ml pa or as ur sa ne kok mni sd ks doi brx sat mai en`

---

## 2. Consent

```json
{
  "consent_id": "uuid",
  "session_id": "uuid",
  "abha_id": "12-3456-7890-1234 | null",
  "consent_version": "2.1",
  "language": "hi",
  "consent_text_hash": "sha256:a3f2...",
  "permissions": {
    "capture":      true,
    "share_his":    true,
    "push_phr":     true,
    "retain_audio": false
  },
  "assent_method": "voice | touch",
  "assent_audio_blob_id": "uuid | null",
  "operator_present": false,
  "granted_at": "iso8601",
  "expires_at": "iso8601",
  "revoked_at": null,
  "supersedes": "uuid | null"
}
```

**Rules**
- `capture` is the only mandatory permission. False → session ends, nothing retained.
- `retain_audio: false` → audio blobs deleted after transcription. Provenance degrades to transcript text. **This is correct behaviour, not a bug.**
- Immutable. Revocation writes a **new row** with `supersedes` pointing at the original.

---

## 3. Slot — M3 → M5

```json
{
  "slot_id": "uuid",
  "session_id": "uuid",
  "ontology_key": "hpi.pain.radiation",
  "value": ["left_arm"],
  "value_type": "string | number | boolean | enum | enum_multi | scale",
  "unit": null,
  "confidence": 0.94,
  "framework": "socrates | ros | dashavidha | demographics | general",
  "section": "hpi",
  "answered_by": "self | proxy",
  "input_mode": "voice | touch",
  "provenance_id": "uuid",
  "superseded_by": null,
  "created_at": "iso8601"
}
```

**`ontology_key` namespace** — dotted, stable, defined in `ontology/*.yaml`:

```
demographics.age            hpi.pain.site          ros.cardio.chest_pain
demographics.sex            hpi.pain.onset         ros.resp.cough
cc.text                     hpi.pain.character     dashavidha.prakriti.appetite
cc.duration_days            hpi.pain.radiation     dashavidha.agni
pmh.conditions              hpi.pain.associations  dashavidha.koshtha
psh.procedures              hpi.pain.time_course   ahara_vihara.meal_timing
drugs.current               hpi.pain.exacerbating  ahara_vihara.sleep
allergy.list                hpi.pain.relieving     nidana.patient_belief
family.conditions           hpi.pain.severity
personal.habits
```

**Confidence bands:** `>0.85` accept · `0.6–0.85` accept + confirm in recap · `<0.6` ask a clarifying closed question.

---

## 4. DocEntity — M4 → M5

```json
{
  "entity_id": "uuid",
  "session_id": "uuid",
  "document_id": "uuid",
  "document_type": "prescription | lab_report | discharge_summary | imaging_report | id_card",
  "entity_type": "medicine | diagnosis | lab_value | procedure | vital",
  "payload": { },
  "event_date": "2025-01-14",
  "date_source": "explicit | inferred | patient | none",
  "confidence": 0.88,
  "ocr_confidence": 0.91,
  "ner_confidence": 0.96,
  "lexicon_match": 1.0,
  "needs_verification": false,
  "verified_by": null,
  "verified_value": null,
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

### 4.1 `payload` shapes by `entity_type`

**medicine**
```json
{ "name": "Metformin", "normalised_name": "metformin",
  "strength": 500, "strength_unit": "mg",
  "frequency": "BD", "frequency_raw": "1-0-1",
  "duration_days": 30, "route": "oral", "form": "tablet" }
```

**lab_value**
```json
{ "analyte": "HbA1c", "loinc": "4548-4",
  "value": 9.2, "unit": "%",
  "ref_low": 4.0, "ref_high": 5.6,
  "ref_source": "document | builtin",
  "is_abnormal": true, "direction": "high" }
```

**diagnosis**
```json
{ "text": "Type 2 Diabetes Mellitus", "icd11": "5A11", "namaste": null, "snomed": "44054006" }
```

**procedure**
```json
{ "text": "Coronary angiography", "icd11": null, "performed_on": "2024-11-03" }
```

**vital**
```json
{ "name": "blood_pressure", "systolic": 148, "diastolic": 92, "unit": "mmHg" }
```

### 4.2 Abstention entity

When `confidence < 0.60`, M4 emits **no decoded value**:

```json
{ "entity_type": "medicine",
  "payload": { "name": null, "raw_ocr_guess": "Melformn 50?" },
  "confidence": 0.41,
  "needs_verification": true,
  "source": { "type": "image_bbox", "page": 2, "bbox": [180,412,520,448], "crop_blob_id": "uuid" } }
```

**Bounding boxes are in ORIGINAL image pixel space**, not the preprocessed image. M4 must transform them back after dewarp/deskew or "show me the ink" shows the wrong region.

---

## 5. Provenance — M3, M4, physician → M5 enforces

```json
{
  "prov_id": "uuid",
  "session_id": "uuid",
  "kind": "audio_offset | image_bbox | physician_entry",
  "audio": { "blob_id": "uuid", "start_ms": 123400, "end_ms": 127800,
             "transcript_local": "बाएँ हाथ तक", "transcript_english": "up to the left arm" },
  "image": { "blob_id": "uuid", "page": 1, "bbox": [412,88,690,118], "crop_blob_id": "uuid" },
  "created_by": "M3 | M4 | physician",
  "created_at": "iso8601"
}
```

> **HARD RULE — the core guarantee of this project.**
> M5 renders a summary field **only if** it resolves to a valid `prov_id`.
> An unsourced field is **discarded silently**, not flagged. A flagged claim is still a claim on the doctor's screen.

---

## 6. Alert — M3, M4, M5 → M6

```json
{
  "alert_id": "uuid",
  "session_id": "uuid",
  "kind": "red_flag | conflict | abnormal_value | interaction | unreadable",
  "severity": "critical | warning | info",
  "rule_id": "CARDIAC-01 | null",
  "title": "Exertional chest pain with left-arm radiation",
  "detail": "Patient reports radiation to left arm with diaphoresis.",
  "evidence_refs": ["slot_id", "entity_id"],
  "raised_by": "M3 | M4 | M5",
  "raised_at": "iso8601",
  "acknowledged_by": null,
  "acknowledged_at": null
}
```

**Alerts state facts. They never advise.** `"Warfarin and Aspirin both present"` — never `"stop the aspirin"`. Guardian will block the second form.

---

## 7. ClinicalSummary — M5 → M1 / M6 / frontend

```json
{
  "summary_id": "uuid",
  "session_id": "uuid",
  "status": "draft | edited | signed",
  "sections": {
    "chief_complaint": [{ "text": "Chest pain, 3 days", "provenance": ["prov_id"], "answered_by": "self" }],
    "hpi":             [],
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
    "prakriti": { "vata": 0.44, "pitta": 0.36, "kapha": 0.20,
                  "dominant": "vata-pitta", "confidence": 0.71,
                  "items_answered": 24, "items_total": 30 },
    "vikriti": "...",
    "agni": "vishamagni",
    "koshtha": "krura",
    "ahara_vihara": ["irregular meal timing", "night shift work"],
    "codes": { "namaste": "AAE-16", "icd11_tm2": "SF7Y" }
  },
  "timeline": [
    { "date": "2024-11-03", "type": "prescription",
      "summary": "Metformin 500 BD started",
      "entity_ids": ["uuid"], "provenance": "prov_id" }
  ],
  "undated": [],
  "delta": {
    "is_return_visit": true, "visit_number": 3,
    "changed": ["pain 4/10 (was 8/10)", "NEW: ankle oedema"],
    "adherence_estimate": 0.6,
    "adherence_reason": "patient reports missing evening dose"
  },
  "alerts": ["alert_id"],
  "guardian": { "checked": true, "blocked_count": 0, "version": "g-1.2" },
  "fields_dropped_unsourced": 3,
  "generated_at": "iso8601",
  "signed_by": null,
  "signed_at": null
}
```

**Section order is fixed** and matches the PS: CC → HPI → PMH → PSH → Drugs → Allergy → Family → Personal → ROS → Investigations.

**Every `sections[*]` item carries a non-empty `provenance` array.** If it does not, M5 has a bug.

---

## 8. Correction — M6 → M5 / M3 / M4

```json
{
  "correction_id": "uuid",
  "summary_id": "uuid",
  "section": "drugs",
  "field_path": "sections.drugs[1].text",
  "generated_value": "Telmisartan 40 OD",
  "corrected_value": "Telmisartan 40 BD",
  "source_module": "M3 | M4 | M5",
  "source_prov_id": "uuid",
  "corrected_by": "physician_id",
  "corrected_at": "iso8601"
}
```

Routed back: M4-sourced → OCR training pair. M3-sourced → slot-filling or ASR issue.

---

## 9. Language service payloads — M2

**STT request / response**
```json
// →
{ "session_id": "uuid", "audio_b64": "...", "source_lang": "hi", "chain_translation": true }
// ←
{ "text_local": "बाएँ हाथ तक", "text_english": "up to the left arm",
  "blob_id": "uuid", "start_ms": 123400, "end_ms": 127800,
  "asr_confidence": 0.91, "negation_hint": false, "engine": "bhashini | local" }
```

**TTS request / response**
```json
// →
{ "session_id": "uuid", "text_english": "Does the pain spread anywhere?",
  "target_lang": "hi", "voice": "female" }
// ←
{ "audio_url": "...", "text_local": "दर्द कहाँ तक जाता है?", "cached": true, "engine": "bhashini" }
```

**Protected-term masking** — the translator never sees these. Token format `⟦{type}{id:04d}⟧`, e.g. `Metformin → ⟦D0421⟧`, `Vata → ⟦A0003⟧`. If any `⟦...⟧` survives into the output, M2 falls back to the unmasked source and logs it.

---

## 10. Conversation turn — M3

```json
// →
{ "text_english": "up to the left arm",
  "audio_provenance_ref": "prov_id",
  "asr_confidence": 0.91,
  "negation_hint": false,
  "touch_selection": null,
  "answered_by": "self" }
// ←
{ "slots_filled": ["slot_id"],
  "next_question": {
    "text_en": "Does anything make it worse?",
    "text_local": "किससे बढ़ता है?",
    "audio_url": "...",
    "slot_keys": ["hpi.pain.exacerbating"],
    "options": [{ "key": "exertion", "label_local": "चलने पर", "icon": "walk" }],
    "input_modes": ["voice", "touch"]
  },
  "progress": { "section": "hpi", "percent": 42, "questions_asked": 11,
                "estimated_remaining_s": 180 },
  "red_flag": null,
  "state": "continue | complete | aborted" }
```

**Red-flag positive:**
```json
{ "red_flag": { "rule_id": "CARDIAC-01", "severity": "critical",
                "message_key": "rf.cardiac.stop",
                "message_local": "कृपया यहीं रुकें। नर्स अभी आ रही हैं।" },
  "state": "aborted" }
```
Partial slots are **preserved** and still flow to M5.

---

## 11. Threshold reference — use these exact values everywhere

```
Slot confidence      >= 0.85 accept · 0.60–0.85 confirm · < 0.60 clarify
Entity confidence    >= 0.85 auto  · 0.60–0.85 soft-verify · < 0.60 ABSTAIN
Turn latency         p50 < 2.5 s   · p95 < 3.5 s   · hard ceiling 3 s target
OCR job              soft 15 s     · hard timeout 60 s
Interview            time budget 8 min · idle timeout 90 s
Session vault TTL    2 hours
Bhashini timeout     4 s → fall through to local
FHIR push            5 s timeout · 5 retries · exponential backoff
```

---

## 12. Storage layout (MinIO)

```
purva-audio/{session_id}/turn-{n}.wav
purva-audio/{session_id}/consent-assent.wav
purva-audio/{session_id}/segments/{prov_id}.wav      ← pre-cut, cached
purva-documents/{session_id}/{document_id}/original.jpg     ← never delete before retention
purva-documents/{session_id}/{document_id}/processed.jpg
purva-documents/{session_id}/{document_id}/crops/{entity_id}.jpg
purva-tts-cache/{lang}/{hash}.wav
purva-consent-audio/{version}/{lang}.wav             ← pre-generated, long-lived
```

Retention is driven by `Consent.permissions`. Default: audio and originals deleted at session end.

---

## 13. Error envelope — every endpoint

```json
{ "error": { "code": "CONSENT_REQUIRED",
             "message": "Session has no valid consent artefact.",
             "request_id": "uuid",
             "retryable": false } }
```

**Codes:** `CONSENT_REQUIRED` `SESSION_EXPIRED` `SESSION_NOT_FOUND` `ABHA_UNAVAILABLE` `LANG_UNSUPPORTED` `ASR_EMPTY` `OCR_FAILED` `GUARDIAN_UNAVAILABLE` `LLM_UNAVAILABLE` `CONTRACT_VERSION_MISMATCH` `RATE_LIMITED`

---

## 14. Async job envelope

```json
{ "job_id": "uuid", "type": "ocr | fhir_push | tts_prewarm",
  "session_id": "uuid", "status": "queued | processing | done | failed",
  "attempts": 0, "max_attempts": 5, "last_error": null,
  "created_at": "iso8601", "finished_at": null }
```

POST returns `202` with `{ job_id, poll_url }`. Dead-lettered jobs surface on the admin dashboard — **never silently discarded**.

---

## 15. Never in a URL or query string

Names, phone numbers, ABHA IDs, transcripts, any clinical value. Session IDs are opaque UUIDs. Everything sensitive goes in a request body over TLS.

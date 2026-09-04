# API SPEC — PURVA

Base path `/api/v1` · JSON everywhere · TLS everywhere · ISO 8601 timestamps with timezone.
Object shapes live in [`DATA_CONTRACTS.md`](DATA_CONTRACTS.md). This file is the route list.

**M6 owns this file.** A new route or a changed shape requires a message to the team.

---

## Conventions

| | |
|---|---|
| **Auth — kiosk** | `X-Kiosk-Key: <per-device key>` |
| **Auth — staff** | `Authorization: Bearer <JWT>` with `role: physician \| nurse \| admin` |
| **Auth — patient** | `Authorization: Bearer <JWT>` scoped to own ABHA |
| **Request id** | `X-Request-ID` — generated if absent, echoed, logged |
| **Idempotency** | `Idempotency-Key` on every POST that creates a resource |
| **Pagination** | `?limit=50&cursor=...` |
| **Async** | POST returns `202 { job_id, status, poll_url }` |
| **Errors** | see DATA_CONTRACTS §13 |

**Never put PII in a path or query string.**

---

## Health — M6

| Method | Path | Auth | Returns |
|---|---|---|---|
| GET | `/health` | none | `{ status, version, contract_version }` |
| GET | `/ready` | none | `200` only when **all models loaded** and DB reachable |
| GET | `/health/deps` | staff | per-dependency: postgres, redis, minio, bhashini, llm, abdm |

> `/ready` is not optional. A kiosk that accepts a patient before the ASR model is resident will hang on question one, on stage.

---

## Session & Identity — M1

| Method | Path | Body | Returns |
|---|---|---|---|
| POST | `/session` | `{ language, kiosk_id, opd_type }` | `{ session_id, state: "created" }` |
| POST | `/session/{id}/identity` | `{ method: "qr\|otp\|aadhaar\|new", payload }` | `{ abha_id?, demographics?, requires_otp, txn_id? }` |
| POST | `/session/{id}/identity/verify-otp` | `{ txn_id, otp }` | `{ abha_id, demographics }` |
| GET | `/session/{id}` | — | `Session` |
| POST | `/session/{id}/purge` | — | `{ purged: true, blobs_deleted: 4 }` |

**Identity failure never blocks intake.** On failure, create a local-only session with `phr_linked: false` and continue.

---

## Consent — M1

| Method | Path | Body | Returns |
|---|---|---|---|
| GET | `/consent/text?lang=hi&version=latest` | — | `{ version, text, hash, audio_url }` |
| POST | `/session/{id}/consent` | `{ permissions, assent_method, assent_audio_blob_id }` | `{ consent_id, state: "consented" }` |
| POST | `/consent/{id}/revoke` | `{ reason }` | `{ revoked_at, supersedes }` |
| GET | `/consent/{id}` | — | `Consent` |

`consent/text` returns a **pre-generated** `audio_url`. Never synthesise 300 words of TTS live.

---

## Language — M2

| Method | Path | Body | Returns |
|---|---|---|---|
| POST | `/lang/stt` | `{ session_id, audio_b64, source_lang, chain_translation }` | text_local, text_english, blob_id, offsets, asr_confidence, negation_hint, engine |
| POST | `/lang/tts` | `{ session_id, text_english, target_lang, voice }` | `{ audio_url, text_local, cached, engine }` |
| POST | `/lang/translate` | `{ text, source_lang, target_lang, protect_terms }` | `{ text, masked_count, engine }` |
| POST | `/lang/tts/prewarm` | `{ texts: [...], target_lang }` | `{ warmed: 3 }` |
| GET | `/lang/languages` | — | `[{ code, name_native, name_en, stt, tts, nmt }]` |
| GET | `/lang/health` | — | `{ bhashini, local_models, latency_p50_ms }` |

Callers **never branch on `engine`**. Online and offline return the identical shape.

---

## Conversation — M3

| Method | Path | Body | Returns |
|---|---|---|---|
| POST | `/session/{id}/interview/start` | `{ opd_type, is_return_visit }` | first question + progress |
| POST | `/session/{id}/turn` | turn payload (DATA_CONTRACTS §10) | slots_filled, next_question, progress, red_flag, state |
| POST | `/session/{id}/skip` | — | next question |
| POST | `/session/{id}/interview/end` | — | `{ slot_count, sections_covered, duration_s, end_reason }` |
| GET | `/session/{id}/slots` | — | `[Slot]` |
| GET | `/session/{id}/resume` | — | `{ resumable, last_slot, next_question }` |
| GET | `/ontology/questions?section=hpi&lang=hi` | — | question definitions for frontend pre-render |

**Latency budget for `/turn`: p95 under 3 s**, including the M2 round trips.

---

## Documents — M4

| Method | Path | Body | Returns |
|---|---|---|---|
| POST | `/session/{id}/document/qc` | `{ frame_b64 }` | `{ ok, reason, hint_key, hint_text_local }` — **must return < 150 ms** |
| POST | `/session/{id}/document` | `{ image_b64, page_hint? }` | `202 { document_id, job_id, poll_url }` |
| GET | `/session/{id}/document/{document_id}` | — | `{ status, document_type, entities, page_count }` |
| GET | `/session/{id}/entities` | — | `[DocEntity]` |
| GET | `/session/{id}/timeline` | — | `{ timeline, undated, duplicates_removed }` |
| GET | `/session/{id}/verify-queue` | — | `[{ entity_id, crop_url, raw_ocr_guess, confidence }]` |
| POST | `/entity/{entity_id}/verify` | `{ corrected_value, verified_by }` | `{ updated: true, training_pair_id }` |
| GET | `/document/{document_id}/crop?bbox=x,y,w,h` | — | image bytes — powers **"show me the ink"** |

`/document` is **async by contract**. A synchronous 12-second OCR call will time out the gateway and make the kiosk feel broken.

---

## Summary — M5

| Method | Path | Body | Returns |
|---|---|---|---|
| POST | `/session/{id}/summarise` | — | `{ summary_id, status, fields_generated, fields_dropped_unsourced, guardian_blocks }` |
| GET | `/session/{id}/summary` | — | `ClinicalSummary` |
| GET | `/summary/{id}/provenance/{prov_id}` | — | audio segment **or** image crop — **this is the tap-a-line endpoint** |
| PATCH | `/summary/{id}/field` | `{ field_path, corrected_value, corrected_by }` | `{ updated, correction_id }` |
| GET | `/summary/{id}/delta` | — | `{ visit_number, changed, adherence_estimate }` |
| POST | `/session/{id}/recap` | — | `{ text_english, audio_url }` |
| GET | `/session/{id}/prakriti` | — | `{ vata, pitta, kapha, dominant, confidence, items_answered }` |

**`/provenance/{prov_id}` behaviour**

```
consent.retain_audio == true   → { kind: "audio",  url, transcript_local }
consent.retain_audio == false  → { kind: "transcript_only", transcript_local, transcript_english }
image provenance               → { kind: "image", url, page, bbox }
```

Every call **writes an audit event** (`provenance_replayed`). Audio must be **pre-cut server-side** and start playing in under 300 ms.

---

## Doctor — M6

| Method | Path | Auth | Returns |
|---|---|---|---|
| GET | `/doctor/queue` | physician | patients ready, red-flag markers, sorted by priority then token |
| GET | `/doctor/session/{id}/summary` | physician | summary + alerts + timeline + delta |
| PATCH | `/doctor/summary/{id}/field` | physician | apply edit, store correction |
| POST | `/doctor/summary/{id}/sign` | physician | `{ fhir_bundle_id, push_status: "pushed\|queued" }` |

---

## Triage — M6

| Method | Path | Auth | Returns |
|---|---|---|---|
| GET | `/triage/queue` | nurse | live queue + red flags pinned with rule + timestamp |
| WS | `/ws/triage` | nurse | **push** on every queue change — no polling |
| POST | `/triage/{alert_id}/acknowledge` | nurse | `{ acknowledged_at }` |
| GET | `/triage/verify-queue` | nurse | unreadable ink awaiting a human |

The board must update **while the judges are watching**, with no refresh. WebSocket or SSE, not a 5-second poll.

---

## Patient dashboard — M6

| Method | Path | Auth | Returns |
|---|---|---|---|
| GET | `/patient/{abha}/timeline` | patient | every visit, every digitised document |
| GET | `/patient/{abha}/labs?analyte=HbA1c` | patient | values over time for plotting |
| GET | `/patient/{abha}/recap/{session_id}` | patient | audio recap in own language |
| GET | `/patient/{abha}/consents` | patient | active consents |
| POST | `/patient/{abha}/consent/{id}/revoke` | patient | revocation |

---

## FHIR & ABDM — M1

| Method | Path | Returns |
|---|---|---|
| GET | `/session/{id}/fhir` | the FHIR R4 bundle JSON — for demo and debugging |
| POST | `/session/{id}/fhir/push` | `{ bundle_id, status: "pushed \| queued" }` |
| GET | `/fhir/outbox` | pending / failed bundles (admin) |
| POST | `/fhir/outbox/{id}/retry` | force a retry |

---

## Admin & metrics — M6

| Method | Path | Returns |
|---|---|---|
| GET | `/admin/metrics/guardian` | `{ outputs_checked, blocked_diagnostic, blocked_therapeutic, emitted_diagnostic, version }` |
| GET | `/admin/metrics/accuracy?window=7d` | `{ by_section, by_source_module, trend }` |
| GET | `/admin/metrics/latency` | `{ turn_p50_ms, turn_p95_ms, by_stage, engine_mix }` |
| GET | `/admin/metrics/throughput` | `{ sessions_today, avg_duration_s, completion_rate, abandonment_rate, red_flags_fired }` |
| GET | `/admin/jobs/dead-letter` | jobs that exhausted retries |
| GET | `/audit?session_id=...` | audit trail |

`emitted_diagnostic` should read **0**. That number is a demo asset — put it on screen.

---

## WebSocket channels

| Path | Who | Direction | Payload |
|---|---|---|---|
| `/ws/triage` | nurse | server → client | queue updates, red-flag events |
| `/ws/doctor/{physician_id}` | physician | server → client | "patient ready", live summary updates as async OCR lands |
| `/ws/kiosk/{session_id}` | kiosk | bidirectional | optional streaming ASR |

---

## Mock mode

```bash
PURVA_MOCK=m1,m3,m4,m5 docker compose up
```

Every listed module's routes return realistic fixtures from `backend/db/seed/`. Drop your letter once your module is real. **This is how nobody is blocked after day 1.**

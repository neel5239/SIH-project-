# M1 — Identity, Consent & ABDM Integration

> **Owner:** Member 1
> **Read `00-INTRODUCTION.md` first.**
> **Service path:** `services/m1_identity/`
> **Branch:** `m1-identity`

---

## 1. Why this module exists

Two jobs, both non-negotiable for a government deployment:

**Job A — Know who this patient is.**
Every record we build must attach to a real, national health identity (ABHA), or the whole thing is a disconnected local database and the ABDM "first-mile" problem stays unsolved. This module is the *front door*.

**Job B — Prove we were allowed to do it.**
The Digital Personal Data Protection Act 2023 requires informed, granular, revocable consent before processing personal health data. The PS explicitly demands *"granular, revocable consent with audio explanation for low-literacy patients."*

A patient who cannot read cannot give informed consent against a wall of text. **So we speak it.** That is USP #7, and this module owns it.

**Job C — Get the record back out.**
At the end of the session, everything M5 produced must be converted into a valid FHIR R4 bundle and pushed to the patient's ABHA Personal Health Record via the ABDM HIP gateway — or queued on the edge node if the network is down.

### The one sentence

> M1 is the gate at both ends: nothing starts without identity + consent, and nothing leaves without a signed, standards-compliant bundle and an audit trail.

---

## 2. Responsibilities

| # | Responsibility | Detail |
|---|---|---|
| 1 | **ABHA authentication** | QR scan, 14-digit + OTP, Aadhaar fallback, new-patient enrolment |
| 2 | **Language selection** | Capture patient's language choice; hand to M2 for all subsequent audio |
| 3 | **Spoken consent flow** | Version-hashed consent text, read aloud via M2 TTS, spoken assent recorded |
| 4 | **Granular consent toggles** | Separate permissions: capture / share with hospital / push to ABHA / retain audio |
| 5 | **Consent artefact** | Immutable, revocable, auditable record of exactly what was agreed and when |
| 6 | **Session lifecycle** | Create session, hold it in an encrypted TTL-bound vault, purge on completion |
| 7 | **PII minimisation** | Strip identifiers before anything goes to a cloud service |
| 8 | **FHIR R4 mapping** | Convert `ClinicalSummary` → a valid FHIR bundle |
| 9 | **ABDM HIP push** | Post the bundle to the gateway; handle failure and retry |
| 10 | **HIS linkage** | Attach the encounter to the hospital's token/encounter record |
| 11 | **Audit log** | Immutable log of who accessed what, when, under which consent |
| 12 | **Consent revocation** | Patient can revoke later from the dashboard; revocation propagates and is logged |

### Explicitly NOT this module's job

- Anything about *what* the clinical content says (M5)
- Speech recognition or synthesis itself (M2 — M1 only *calls* M2)
- Storing the actual documents or audio blobs (M6 owns storage; M1 owns the *permission* to store them)

---

## 3. Internal pipeline

```
                    Patient arrives at kiosk
                              │
                              ▼
              STEP 1 — LANGUAGE SELECT
              22-language grid
              each option spoken via M2 TTS
                              │
                              │  OUT: language_code
                              ▼
              STEP 2 — IDENTITY
                              │
        ┌───────────┬─────────┼─────────┬───────────┐
        ▼           ▼         ▼         ▼           ▼
     QR scan    14-digit   Aadhaar    New       (any path
                 + OTP               patient     fails)
        │           │         │         │           │
        └───────────┴────┬────┴─────────┘           │
                         ▼                          ▼
              ABDM ABHA verification         LOCAL-ONLY SESSION
                         │                   no PHR push
              ┌──────────┴──────────┐        intake continues
              ▼                     ▼        phr_linked = false
           SUCCESS               FAILURE            │
              │                     │               │
              │                     └───────────────┘
              ▼
        OUT: abha_id · demographics
              │
              ▼
              STEP 3 — CONSENT          ◄── USP #7
              │
              ▼
        load consent text for language + version
              │
              ▼
        SHA-256 hash of exact text
              │
              ▼
        M2 TTS → play audio aloud
              │
              ▼
        show 4 granular toggles (icon + own audio clip)
              │
        ┌─────────┬────────┼────────┬──────────┐
        ▼         ▼        ▼        ▼          ▼
     capture   share    push to   retain    patient
    (required) w/ HIS    ABHA      audio    declines
        │         │        │        │       capture
        └─────────┴───┬────┴────────┘          │
                      │                        ▼
                      ▼                  END SESSION
        patient responds — voice or tap   politely, no
                      │                   data retained
                      ▼
        record spoken assent audio blob
                      │
                      ▼
        OUT: consent_id · CONSENT ARTEFACT
             immutable · revocable · auditable
                      │
                      ▼
              STEP 4 — SESSION CREATE
              write Session object
              store in Redis vault, TTL-bound
              encrypt at rest
              emit session_created
                      │
                      │  OUT: session_id
                      ▼
              M2 / M3 / M4 / M5 may now run
                      │
                      ▼
              ~~~ interview + documents + summary ~~~
                      │
                      ▼
              STEP 5 — FHIR MAPPING
              (after physician signs)
                      │
                      ▼
              ClinicalSummary from M5
                      │
        ┌─────────┬──────────┼──────────┬──────────┐
        ▼         ▼          ▼          ▼          ▼
     Patient  Encounter   Consent   Condition  Observation
                                    (× n dx)   (× n labs)
        │         │          │          │          │
        └─────────┴──────────┼──────────┴──────────┘
                             │
        ┌──────────┬─────────┼─────────┬──────────┐
        ▼          ▼         ▼         ▼          ▼
  Medication  Allergy   Document  Composition  (AYUSH
  Statement  Intolerance Reference (the summary  Prakriti
  (× n drugs)           (× n scans)    doc)    Observation)
        │          │         │         │          │
        └──────────┴────┬────┴─────────┴──────────┘
                        ▼
              BUNDLE (type = document)
                   validated
                        │
                        ▼
              STEP 6 — PUSH
                        │
                    network up?
                        │
              ┌─────────┴─────────┐
              ▼                   ▼
             YES                  NO
              │                   │
              ▼                   ▼
        ABDM HIP gateway     OUTBOX TABLE
        timeout 5 s          status = PENDING
              │              attempts = 0
              │                   │
         push failed?       background worker
              │             exponential backoff
              └─────────┬─────────┘
                        ▼
              status = PUSHED
              + bundle_id + timestamp
                        │
                        ▼
              HIS encounter link
                        │
                        ▼
              STEP 7 — PURGE & AUDIT
              delete session vault entry
              delete audio/images unless retain_audio
              write immutable audit entries
```

---

## 4. Component detail

### 4.1 ABHA authentication

Four entry paths. All converge on the same verification call.

| Path | Flow | When used |
|---|---|---|
| **QR scan** | Camera reads ABHA card QR → contains ABHA number → verify | Patient has physical/digital card. **Fastest — make this the default.** |
| **14-digit + OTP** | Patient speaks or types number → OTP to linked mobile → verify | Card lost, remembers number |
| **Aadhaar** | Aadhaar number + OTP → ABHA lookup/creation | No ABHA yet, has Aadhaar |
| **New patient** | Local record created with name/age/sex/phone; ABHA link deferred | First visit, no ID at all — **must not block them** |

**Design rule:** identity failure must **never** stop the intake. If ABHA cannot be verified, create a *local-only* session. The patient still gets their history taken, the doctor still gets the summary. Only the PHR push is skipped, and the summary is flagged `phr_linked: false`.

```
verify_abha(method, payload) -> AbhaResult
    ├── ok:      { abha_id, name, gender, dob, address }
    ├── otp_req: { txn_id }            # step 2 needed
    └── fail:    { reason }            # → local-only session
```

**Sandbox note:** ABDM provides a public sandbox. Register early — sandbox credentials can take days. **Do this on day 1.** If sandbox access does not arrive in time, build against a local mock that returns the same shapes, and demo with the mock. The FHIR bundle correctness is what judges check, not whether it landed in a real government server.

### 4.2 The spoken consent flow (USP #7)

This is the feature nobody else will build. Get it right.

**Consent text is versioned and hashed.** We store the hash *with* the assent, so we can later prove exactly which wording the patient agreed to.

```
consent/
├── v2.1/
│   ├── hi.txt
│   ├── ta.txt
│   ├── bn.txt
│   └── en.txt
└── manifest.json    # { "version": "2.1", "hashes": { "hi": "sha256:...", ... } }
```

**Flow:**

```
1. load text  = consent/v2.1/{lang}.txt
2. hash       = sha256(text bytes)
3. audio      = M2.tts(text, lang)          ← pre-generate and cache; do not
                                              synthesise 300 words live
4. play audio, show text on screen in large type
5. show 4 granular toggles, each with an icon + its own short audio clip
6. patient responds:  voice "हाँ" / "नहीं"  OR  tap
7. record assent audio blob (3-5 seconds)
8. build artefact
```

**Granular toggles — the four permissions:**

| Key | Plain-language prompt (translated) | If OFF |
|---|---|---|
| `capture` | "May we record what you tell us?" | **Session cannot proceed.** Only mandatory one. |
| `share_his` | "May we show this to your doctor here?" | Summary generated but not pushed to HIS |
| `push_phr` | "May we save this to your ABHA health account?" | No FHIR push |
| `retain_audio` | "May we keep your voice recording?" | Audio deleted immediately after transcription; provenance falls back to transcript text only |

**Note the trade-off on `retain_audio`:** if the patient declines, the tap-a-line-hear-the-audio feature (USP #1) degrades to tap-a-line-see-the-transcript. That is correct behaviour — consent wins over features. Document it, and say so in the demo. It shows maturity.

### 4.3 Consent artefact

```json
{
  "consent_id": "uuid",
  "session_id": "uuid",
  "abha_id": "12-3456-7890-1234 | null",
  "consent_version": "2.1",
  "language": "hi",
  "consent_text_hash": "sha256:a3f2...",
  "permissions": {
    "capture": true,
    "share_his": true,
    "push_phr": true,
    "retain_audio": false
  },
  "assent_method": "voice | touch",
  "assent_audio_blob_id": "uuid | null",
  "granted_at": "2026-09-02T14:22:07+05:30",
  "expires_at": "2027-09-02T14:22:07+05:30",
  "revoked_at": null,
  "revocation_reason": null,
  "kiosk_id": "AIIA-OPD-K03",
  "operator_present": false
}
```

**Immutable.** Never updated in place. Revocation writes a *new* row referencing the original and sets `revoked_at`. The audit trail must show the full history.

### 4.4 Session vault

Redis, TTL-bound, encrypted at rest.

```
Key:    session:{session_id}
Value:  encrypted JSON blob (Session + working state)
TTL:    2 hours (configurable) — hard ceiling on how long
        a patient's data can sit in the vault

On completion  → explicit DEL, do not wait for TTL
On abandonment → TTL cleans up automatically
```

**Why a separate vault instead of just Postgres:** the PS explicitly requires *"temporary session data is cleared immediately after submission."* A TTL-bound cache makes that a structural property, not a cron job that might not run. Postgres holds only the *committed, consented* record.

### 4.5 PII minimisation

Before any call leaves the facility (Bhashini cloud, ABDM):

| Data | Treatment |
|---|---|
| Audio going to Bhashini STT | Send audio only. **No name, no ABHA ID, no session ID in the request.** Use an opaque per-call token. |
| Text going to Bhashini NMT | Names and identifiers masked the same way M2 masks drug names |
| FHIR bundle to ABDM | Full identity is *required and correct* here — this is the patient's own record. Sign it. |

### 4.6 FHIR R4 mapping

`ClinicalSummary` (§9.5 of the intro doc) → FHIR bundle.

| Summary element | FHIR resource | Key fields |
|---|---|---|
| Patient identity | `Patient` | `identifier` = ABHA, `name`, `gender`, `birthDate` |
| The visit | `Encounter` | `class` = AMB (ambulatory), `period`, `serviceType` |
| Consent artefact | `Consent` | `status`, `scope`, `policyRule`, `provision` per permission |
| Each diagnosis | `Condition` | `code` (ICD-11 + NAMASTE), `onsetDateTime`, `recordedDate` |
| Each lab value | `Observation` | `code` (LOINC), `valueQuantity`, `referenceRange`, `interpretation` |
| Each drug | `MedicationStatement` | `medicationCodeableConcept`, `dosage`, `effectivePeriod` |
| Each allergy | `AllergyIntolerance` | `code`, `criticality` |
| Each scanned doc | `DocumentReference` | `content.attachment.url` → MinIO, `type` |
| Prakriti / AYUSH block | `Observation` with NAMASTE code | `component` per dosha with `valueDecimal` |
| The summary itself | `Composition` | sections mirroring CC → HPI → PMH → … |
| Everything | `Bundle` | `type: document`, `entry[]`, signed |

**Validation:** run every bundle through a FHIR validator before push. A malformed bundle is a silent failure in production and an embarrassing one in a demo.

**Practical:** use the `fhir.resources` Python library for construction, and a local HAPI FHIR server in Docker for validation during development.

### 4.7 The AYUSH coding problem

Standard FHIR has no native Prakriti concept. Encode it as an `Observation` with NAMASTE codes:

```json
{
  "resourceType": "Observation",
  "code": { "coding": [{ "system": "https://namaste.ayush.gov.in", "code": "PRAKRITI" }] },
  "component": [
    { "code": { "text": "Vata" },  "valueDecimal": 0.44 },
    { "code": { "text": "Pitta" }, "valueDecimal": 0.36 },
    { "code": { "text": "Kapha" }, "valueDecimal": 0.20 }
  ],
  "note": [{ "text": "confidence 0.71" }]
}
```

Then add the ICD-11 TM2 dual-code alongside. **Show this JSON in the demo** — it is direct evidence of AYUSH-native design, which is exactly what AIIA cares about.

### 4.8 Offline / store-and-forward

```
build bundle
      │
      ▼
try push to ABDM HIP gateway  (timeout 5s)
      │
  ┌───┴───┐
 OK      FAIL / no network
  │        │
  │        ▼
  │   write to outbox table
  │   status = PENDING, attempts = 0
  │        │
  │        ▼
  │   background worker, exponential backoff
  │   retries when connectivity returns
  │        │
  └────┬───┘
       ▼
  status = PUSHED, record bundle_id + timestamp
```

**Demo moment:** pull the network cable, complete a session, plug it back in, show the bundle syncing. This is USP #8 and it lands hard with government judges.

### 4.9 Audit log

Append-only. Never updated, never deleted.

```json
{
  "audit_id": "uuid",
  "timestamp": "iso8601",
  "actor": "patient | physician:{id} | nurse:{id} | system",
  "action": "consent_granted | consent_revoked | summary_viewed | summary_edited | summary_signed | fhir_pushed | session_purged | provenance_replayed",
  "session_id": "uuid",
  "resource_ref": "summary_id | slot_id | entity_id",
  "consent_id": "uuid",
  "outcome": "success | denied | error",
  "detail": "free text"
}
```

`provenance_replayed` matters — when a doctor taps a line and hears the patient's voice, that is an access to sensitive audio and must be logged.

---

## 5. API surface

```
POST   /api/v1/session
       body  { language, kiosk_id, opd_type }
       →     { session_id, state: "created" }

POST   /api/v1/session/{id}/identity
       body  { method: "qr|otp|aadhaar|new", payload: {...} }
       →     { abha_id | null, demographics, requires_otp: bool, txn_id? }

POST   /api/v1/session/{id}/identity/verify-otp
       body  { txn_id, otp }
       →     { abha_id, demographics }

GET    /api/v1/consent/text?lang=hi&version=latest
       →     { version, text, hash, audio_url }

POST   /api/v1/session/{id}/consent
       body  { permissions: {...}, assent_method, assent_audio_blob_id }
       →     { consent_id, state: "consented" }

POST   /api/v1/consent/{id}/revoke
       body  { reason }
       →     { revoked_at }

POST   /api/v1/summary/{id}/sign
       body  { physician_id, signature }
       →     { fhir_bundle_id, push_status: "pushed|queued" }

GET    /api/v1/session/{id}/fhir
       →     the FHIR bundle JSON (for demo / debugging)

POST   /api/v1/session/{id}/purge
       →     { purged: true, blobs_deleted: 4 }

GET    /api/v1/audit?session_id=...
       →     [ audit entries ]
```

---

## 6. Data model (Postgres)

```sql
CREATE TABLE patients (
    patient_id      UUID PRIMARY KEY,
    abha_id         TEXT UNIQUE,
    name_enc        BYTEA,          -- encrypted
    gender          TEXT,
    birth_date      DATE,
    phone_enc       BYTEA,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE sessions (
    session_id      UUID PRIMARY KEY,
    patient_id      UUID REFERENCES patients,
    abha_id         TEXT,
    language        TEXT NOT NULL,
    opd_type        TEXT NOT NULL,          -- allopathic | ayush
    token_number    INT,
    kiosk_id        TEXT,
    state           TEXT NOT NULL,
    is_return_visit BOOLEAN DEFAULT false,
    previous_encounter_id UUID,
    started_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at    TIMESTAMPTZ,
    purged_at       TIMESTAMPTZ
);

CREATE TABLE consents (
    consent_id          UUID PRIMARY KEY,
    session_id          UUID REFERENCES sessions,
    abha_id             TEXT,
    consent_version     TEXT NOT NULL,
    language            TEXT NOT NULL,
    consent_text_hash   TEXT NOT NULL,
    permissions         JSONB NOT NULL,
    assent_method       TEXT NOT NULL,
    assent_audio_blob   UUID,
    granted_at          TIMESTAMPTZ NOT NULL,
    expires_at          TIMESTAMPTZ,
    revoked_at          TIMESTAMPTZ,
    revocation_reason   TEXT,
    supersedes          UUID REFERENCES consents
);

CREATE TABLE fhir_outbox (
    outbox_id       UUID PRIMARY KEY,
    session_id      UUID REFERENCES sessions,
    bundle          JSONB NOT NULL,
    status          TEXT NOT NULL,          -- PENDING | PUSHED | FAILED
    attempts        INT DEFAULT 0,
    last_error      TEXT,
    created_at      TIMESTAMPTZ DEFAULT now(),
    pushed_at       TIMESTAMPTZ
);

CREATE TABLE audit_log (
    audit_id        BIGSERIAL PRIMARY KEY,
    timestamp       TIMESTAMPTZ NOT NULL DEFAULT now(),
    actor           TEXT NOT NULL,
    action          TEXT NOT NULL,
    session_id      UUID,
    resource_ref    TEXT,
    consent_id      UUID,
    outcome         TEXT NOT NULL,
    detail          TEXT
);
-- append-only: REVOKE UPDATE, DELETE on audit_log
```

---

## 7. Dependencies

| Depends on | For what |
|---|---|
| **M2** | TTS to speak the consent text and the language grid |
| **M6** | Database, Redis, MinIO, API gateway, background worker |
| **M5** | The `ClinicalSummary` that gets mapped to FHIR |

| Provides to | What |
|---|---|
| **M3** | `session_id` — M3 cannot start without it |
| **M5** | `consent` permissions (controls whether audio may be retained) and prior encounters |
| **M6** | Audit events, session state |

---

## 8. Failure modes and required behaviour

| Failure | What must happen |
|---|---|
| ABHA service unreachable | Create local-only session. Continue. Flag `phr_linked: false`. **Never block the patient.** |
| OTP not received | Offer Aadhaar path, then new-patient path. Timebox each attempt to 30s. |
| Patient declines `capture` | End session politely with audio explanation. Log the refusal. No data retained. |
| Patient declines `push_phr` | Everything works; skip the FHIR push. Doctor still gets the summary. |
| Consent audio fails to play | Fall back to large-text display + a staff-assist button. Do not proceed silently. |
| FHIR validation fails | Do **not** push. Write to outbox with `status=FAILED` and the validation error. Alert admin dashboard. |
| ABDM push rejected | Retry with backoff. After 5 attempts, surface on admin dashboard. Never lose the bundle. |
| Purge fails | Retry. If still failing, alert — this is a compliance breach, not a minor bug. |

---

## 9. Testing

**Unit**
- Consent hash is stable for identical text, different for a changed byte
- Revocation creates a new row and preserves the original
- Each permission toggle correctly gates its downstream action

**Integration**
- Full flow: QR → consent → session → (mock M3/M5) → sign → bundle → push
- Offline flow: disconnect → complete session → reconnect → bundle syncs
- Decline `retain_audio` → verify audio blobs are actually deleted from MinIO

**FHIR conformance**
- Every generated bundle validates against a local HAPI FHIR server
- Round-trip: bundle → parse → all clinical facts recoverable

**Compliance**
- Audit log has an entry for every sensitive access
- `audit_log` rejects UPDATE and DELETE
- Session vault entry is gone within 1 second of `purge`

---

## 10. Build order

**Phase 1 (vertical slice)**
- [ ] Mock ABHA login returning a fixed patient
- [ ] Consent text files for Hindi + English, hashing working
- [ ] Consent recorded (touch only, no audio yet)
- [ ] Session created in Redis with TTL
- [ ] `POST /session`, `POST /consent` live

**Phase 2 (depth)**
- [ ] Real ABDM sandbox integration (all 4 identity paths)
- [ ] Spoken consent via M2 TTS, pre-generated audio cached
- [ ] Granular toggles with per-toggle audio
- [ ] Spoken assent recording
- [ ] Full FHIR R4 bundle construction + validation
- [ ] Audit log, append-only

**Phase 3 (differentiators)**
- [ ] Offline outbox + store-and-forward worker
- [ ] Consent revocation from patient dashboard
- [ ] Purge verification (prove blobs are gone)
- [ ] `provenance_replayed` audit events

---

## 11. Demo checklist — what M1 must show

1. **ABHA QR scan** — card held to camera, patient identified in 2 seconds
2. **Consent spoken aloud in Hindi** — say the words "Digital Personal Data Protection Act 2023" while it plays
3. **Patient says "हाँ"** — show the assent being recorded with the text-hash
4. **The FHIR bundle** — open the JSON, point at the `Consent` resource and the NAMASTE-coded Prakriti `Observation`
5. **Pull the network cable** — complete a session, plug back in, show the bundle syncing from the outbox
6. **The audit log** — every access listed, including the doctor replaying the patient's audio

---

## 12. Notes and gotchas

- **Register for the ABDM sandbox on day 1.** It is the single longest-lead-time dependency in the project.
- **Pre-generate consent audio.** Synthesising 300 words of TTS live adds 4+ seconds to every session. Generate once per (version, language), cache in MinIO, serve the URL.
- **Do not put PII in URLs or query strings.** Ever. Session IDs are opaque UUIDs; ABHA IDs go in request bodies over TLS.
- **Encrypt `name` and `phone` at the column level**, not just at rest. If someone dumps the DB, demographics should not be readable.
- **The consent version must be in the artefact**, not just the text. When you change the wording during development, old consents must still be interpretable.
- **`operator_present` field matters** — if a hospital staff member helped the patient through the kiosk, that changes the consent's legal character. Capture it.

# M2 — Language Layer (Bhashini)

> **Owner:** Member 2
> **Read `00-INTRODUCTION.md` first.**
> **Service path:** `services/m2_language/`
> **Branch:** `m2-language`

---

## 1. Why this module exists

PURVA must talk to a patient who may speak Tamil, may be unable to read, and may be sitting in a noisy OPD hall. Every other module in this project — the dialogue engine, the summary generator, the safety classifier — is written **in English**.

M2 is the bridge between those two worlds. It is the **ear and the mouth** of the system.

### The architectural decision this module implements

> **All clinical reasoning happens in English. Language handling happens only at the edges, only here.**

This is called an **interlingua architecture**, and it is worth stating in the pitch by name.

```
   22 languages IN ──► [M2] ──► ENGLISH ──► M3 / M5 clinical logic
                                   │
   22 languages OUT ◄── [M2] ◄── ENGLISH ◄── M3 / M5 clinical logic
```

**Why it matters:**
- Medical logic, ontologies, red-flag rules and the Guardian are written **once**, in English, and work for every language
- Adding the 23rd language costs **zero clinical engineering** — one config entry
- Medical NLP models, SNOMED, LOINC, ICD-11 are all English-native

**Why Bhashini specifically (not Google/Azure):**
1. **Sovereignty** — patient audio does not leave Indian government infrastructure. On a Ministry of Ayush problem statement, judged by government-adjacent evaluators, this is a scoring point, not a footnote.
2. **Cost** — free/near-free at pilot scale. A foreign cloud STT bill for 5,000 patients/day kills deployability.
3. **Coverage** — 22 scheduled languages out of the box, backed by AI4Bharat models (IndicWhisper, IndicTrans2, Indic-TTS) from IIT Madras.
4. **Alignment** — Bhashini is already the mandated language layer for Indian government digital services. We plug into national infrastructure rather than building a parallel one.

---

## 2. Responsibilities

| # | Responsibility | Detail |
|---|---|---|
| 1 | **Speech to text (STT)** | Patient audio in any supported language → text |
| 2 | **Translation (NMT)** | Local language ↔ English, both directions |
| 3 | **Text to speech (TTS)** | English question → spoken audio in patient's language |
| 4 | **Protected-term masking** | Drug names and Ayurveda terms are masked before translation and restored after — **the translator must never touch them** |
| 5 | **Code-mix normalisation** | Real speech is "मुझे 2 din se fever hai" — handle it |
| 6 | **Voice activity detection + noise suppression** | OPD halls are loud |
| 7 | **Pipeline orchestration** | Chain STT → NMT in a single Bhashini call to cut latency |
| 8 | **Offline fallback** | Local quantised models when Bhashini is unreachable — transparent to callers |
| 9 | **Audio blob management** | Store audio with byte offsets so M3 can attach `audio_offset` provenance |
| 10 | **Printed Indic OCR (optional)** | Bhashini also offers OCR for printed Indic text — offered to M4 as one option |

### Explicitly NOT this module's job

- Deciding *what* question to ask (M3)
- Understanding the clinical meaning of what was said (M3)
- Handwriting OCR (M4 — Bhashini cannot do this)

---

## 3. Internal pipeline

### 3.1 Inbound — patient speaks

```
                    MICROPHONE (kiosk)
                    16 kHz mono PCM
                            │
                            ▼
              VAD — voice activity detection
              detect speech start / end
              trim silence
              reject < 300 ms as noise
                            │
                            ▼
              NOISE SUPPRESSION
              RNNoise / webrtc-ns
              tuned on OPD-hall ambience
                            │
                            ▼
              STORE AUDIO BLOB
              → MinIO, get blob_id
              → record start / end offsets
              ◄── this is the provenance anchor
                            │
                            ▼
                       ROUTE
                            │
              ┌─────────────┴─────────────┐
              ▼                           ▼
           ONLINE                      OFFLINE
              │                           │
              ▼                           ▼
      Bhashini STT              local IndicConformer
      timeout 4 s                   (edge node)
              │                           │
       timed out? ────────────────────────┤
              │                           │
              └─────────────┬─────────────┘
                            ▼
              RAW TRANSCRIPT (local script)
              "मुझे 2 din se bukhar hai"
                            │
                            ▼
              CODE-MIX NORMALISER
              romanised Hindi → Devanagari
              English tokens kept as-is
              numerals normalised
                            │
                            ▼
              NEGATION DETECTION
              flag negation markers before NMT
              → negation_hint
                            │
                            ▼
              PROTECTED-TERM MASK
              scan lexicon: drugs · Ayurveda terms
              · analytes · patient name
              Metformin → ⟦D0421⟧
              Vata      → ⟦A0003⟧
                            │
                            ▼
              NMT → ENGLISH
              Bhashini / local IndicTrans2
                            │
                            ▼
              UNMASK
              ⟦D0421⟧ → Metformin
                            │
                            ▼
              ENGLISH TEXT + provenance ref
              + asr_confidence + negation_hint
                            │
                            ▼
                        → M3
```

### 3.2 Outbound — system speaks

```
              ENGLISH QUESTION from M3
              "Where does the pain spread to?"
                        │
                        ▼
              PROTECTED-TERM MASK
                        │
                        ▼
              NMT → patient language
              Bhashini / local IndicTrans2
                        │
                        ▼
              UNMASK protected terms
                        │
                        ▼
              TTS CACHE LOOKUP
              hash(text + lang + voice)
                        │
              ┌─────────┴─────────┐
              ▼                   ▼
             HIT                 MISS
              │                   │
              │                   ▼
              │                 TTS
              │         Bhashini / local Indic-TTS
              │                   │
              └─────────┬─────────┘
                        ▼
                    AUDIO OUT
                → kiosk speaker
                        +
              localised TEXT → kiosk screen
```

**Cache aggressively.** Most questions in a clinical interview repeat across patients. A warm cache turns a 900ms TTS call into a 5ms disk read.

---

## 4. Component detail

### 4.1 Bhashini / ULCA integration

Bhashini exposes models through **ULCA** (Universal Language Contribution API). Two-step flow:

```
STEP 1 — get pipeline config  (do this ONCE, cache it)
    POST  meity-auth pipeline-config endpoint
    headers: userID, ulcaApiKey
    body:  { pipelineTasks: [ {taskType:"asr", config:{language:{sourceLanguage:"hi"}}},
                              {taskType:"translation", config:{language:{sourceLanguage:"hi",
                                                                        targetLanguage:"en"}}} ],
             pipelineRequestConfig: { pipelineId: "<id>" } }
    →  returns: serviceId per task, the compute endpoint URL, an inference auth key

STEP 2 — run inference  (every turn)
    POST  <compute endpoint from step 1>
    headers: <inference auth key>
    body:  { pipelineTasks: [...with serviceIds...],
             inputData: { audio: [{ audioContent: "<base64>" }] } }
    →  returns: transcript, and translated text if translation was chained
```

**Critical optimisation:** step 1 is slow and its result rarely changes. **Cache the pipeline config per (source language, task chain) with a long TTL.** Calling it every turn adds a full round-trip to every question and will make the kiosk feel broken.

**Critical optimisation 2:** chain `asr` + `translation` in **one** pipeline call. Two separate calls = two network round trips. One chained call = one.

> **Verify the exact endpoint paths and payload shapes against the current Bhashini docs before coding.** Government API surfaces change. The two-step *shape* above is stable; field names may not be.

### 4.2 Protected-term masking — the important one

**The problem:** an NMT model will happily translate, transliterate, or mangle a drug name. `Metformin` may come back as `मेटफॉर्मिन` or, worse, as a semantically "translated" word. `Vata` may become "wind". Both are clinically catastrophic.

**The fix:** never let the translator see them.

```
LEXICON  (loaded from ontology/)
├── drugs.txt        ~15k entries — CDSCO + Jan Aushadhi brand + generic
├── ayurveda.txt     Vata, Pitta, Kapha, Agni, Koshtha, Prakriti, Vikriti, ...
├── analytes.txt     HbA1c, creatinine, TSH, haemoglobin, ...
└── session-scoped   patient name, doctor name, place names

MASK
    input:  "मुझे Metformin से Vata बढ़ता है"
    scan against lexicon (longest-match-first, case-insensitive,
                          fuzzy tolerance for ASR spelling drift)
    output: "मुझे ⟦D0421⟧ से ⟦A0003⟧ बढ़ता है"
            + map { "⟦D0421⟧": "Metformin", "⟦A0003⟧": "Vata" }

TRANSLATE
    "⟦D0421⟧ increases my ⟦A0003⟧"

UNMASK
    "Metformin increases my Vata"
```

**Token format matters.** Use a delimiter the NMT model will not split or translate. `⟦Dnnnn⟧` (mathematical white square brackets) survives most tokenisers. Test this — if the model splits or reorders tokens, switch format.

**Fuzzy matching for ASR drift.** ASR will produce "met formin", "metformine", "मेटफॉर्मिन". The masker must catch these. Use phonetic matching (Double Metaphone / Soundex adapted for Indic) plus edit distance against the lexicon, with a conservative threshold — a false mask is worse than a miss, because it hides a real word.

### 4.3 Code-mix normalisation

Real Indian speech is not monolingual:

```
"मुझे 2 din se fever hai aur stomach में pain"
"enakku rendu naala fever iruku"
"pet mein dard ho raha hai since morning"
```

Pure-Hindi ASR degrades badly on this. Handling:

| Case | Treatment |
|---|---|
| Romanised Hindi in a Devanagari transcript | Transliterate to Devanagari before NMT |
| English medical/common words embedded | **Leave as English.** Do not force-translate. Mark them so the masker and NMT skip them. |
| Numerals in mixed scripts | Normalise to Arabic numerals |
| Time expressions ("do din se", "2 days se") | Normalise to a canonical duration before it reaches M3 |

**Practical note:** M3's slot filler is an LLM operating on English. It is fairly robust to imperfect input. Do not over-engineer this. Fix the cases that break *clinical meaning* (durations, numbers, negations) and let the rest ride.

### 4.4 Negation — a special hazard

`"नहीं, मुझे बुखार नहीं है"` → if the negation is dropped in translation, M3 records `fever = true`. This is the single most dangerous translation failure in the whole system.

**Mitigation:**
1. Detect negation markers in the source language before translation
2. Attach a `negation_hint: true` flag alongside the translated text
3. M3's slot filler receives both and treats a conflict between them as low confidence → asks a confirming question

Never rely on the translator to preserve negation silently.

### 4.5 Offline fallback

```
                       request
                          │
                          ▼
                    HEALTH CHECK
                    cached 30 s
                          │
              ┌───────────┴───────────┐
              ▼                       ▼
           ONLINE                  OFFLINE
              │                       │
              ▼                       ▼
        Bhashini API          LOCAL MODELS on edge node
        timeout 4 s           IndicConformer / IndicWhisper
              │               IndicTrans2 (quantised)
          timed out?          Indic-TTS
              │                       │
              └───────────┬───────────┘
                          ▼
                 SAME RESPONSE SHAPE
                 + engine: "bhashini" | "local"

        the caller never branches on this
```

**The caller must not care which engine ran.** Same request shape, same response shape, one extra field for observability. M3 never branches on this.

**Model sizes to target on a ₹40k edge node:**
| Model | Target |
|---|---|
| ASR | 4-bit quantised, < 1.5 GB, real-time factor < 0.4 |
| NMT | distilled/quantised, < 1 GB |
| TTS | small vocoder, < 500 MB |

Preload all three at boot. Cold-loading a model mid-session is a 20-second stall.

### 4.6 Latency budget

The whole turn — patient stops speaking → next question starts playing — must fit in **~3 seconds**. Beyond that the kiosk feels broken and the queue backs up.

| Stage | Budget |
|---|---|
| VAD end-of-speech detection | 300 ms |
| Noise suppression | 50 ms |
| STT + NMT (chained, one call) | 1200 ms |
| Mask/unmask | 20 ms |
| M3 dialogue decision | 400 ms |
| NMT out | 300 ms |
| TTS (cache hit) | 30 ms |
| TTS (cache miss) | 800 ms |
| Audio playback start | 100 ms |
| **Total (cache hit)** | **~2.4 s** ✅ |
| **Total (cache miss)** | **~3.2 s** ⚠ |

**Optimisations to implement:**
- Cache TTS by `hash(text, lang, voice)` — most questions repeat
- **Pre-synthesise the likely next questions** while the patient is still speaking. The dialogue manager can usually name its top 3 candidates. Warm the cache speculatively.
- Stream audio to STT rather than waiting for end-of-speech where the API supports it
- Keep the pipeline config cached

### 4.7 Audio blob and provenance

M2 is where the audio provenance anchor is created. Every transcript segment must carry the offsets that let M5/M6 replay it.

```json
{
  "blob_id": "uuid",
  "session_id": "uuid",
  "format": "wav/16k/mono",
  "duration_ms": 187400,
  "storage_ref": "minio://purva-audio/{session}/{blob}.wav",
  "segments": [
    {
      "start_ms": 123400,
      "end_ms": 127800,
      "raw_transcript": "बाएँ हाथ तक",
      "translated": "up to the left arm",
      "engine": "bhashini",
      "asr_confidence": 0.91,
      "negation_hint": false
    }
  ],
  "retain": false
}
```

`retain` comes from M1's consent artefact (`permissions.retain_audio`). If false, the blob is deleted after the session and provenance degrades to transcript text.

---

## 5. API surface

```
POST   /api/v1/lang/stt
       body  { session_id, audio_b64, source_lang, chain_translation: true }
       →     { text_local, text_english, blob_id, start_ms, end_ms,
               asr_confidence, negation_hint, engine }

POST   /api/v1/lang/tts
       body  { session_id, text_english, target_lang, voice: "female|male" }
       →     { audio_url, text_local, cached: bool, engine }

POST   /api/v1/lang/translate
       body  { text, source_lang, target_lang, protect_terms: true }
       →     { text, masked_count, engine }

POST   /api/v1/lang/tts/prewarm
       body  { texts: [...], target_lang }
       →     { warmed: 3 }              # speculative pre-synthesis

GET    /api/v1/lang/health
       →     { bhashini: "up|down", local_models: "loaded", latency_p50_ms }

GET    /api/v1/lang/languages
       →     [ { code, name_native, name_en, stt: true, tts: true, nmt: true } ]
```

---

## 6. Configuration

```yaml
# config/m2_language.yaml
bhashini:
  user_id:      ${BHASHINI_USER_ID}
  api_key:      ${BHASHINI_API_KEY}
  timeout_ms:   4000
  config_cache_ttl_s: 86400

local_fallback:
  enabled: true
  asr_model:  models/indicconformer-q4.gguf
  nmt_model:  models/indictrans2-distilled-q8
  tts_model:  models/indic-tts-small
  preload_at_boot: true

languages:
  primary:   [hi, en]                     # must work perfectly
  secondary: [ta, te, bn, mr, gu, kn, ml, pa, or, as]
  # remaining scheduled languages enabled by config only

masking:
  lexicons:
    - ontology/drugs.txt
    - ontology/ayurveda.txt
    - ontology/analytes.txt
  fuzzy_threshold: 0.88
  token_format: "⟦{type}{id:04d}⟧"

tts_cache:
  backend: minio
  ttl_days: 30

audio:
  sample_rate: 16000
  channels: 1
  vad_aggressiveness: 2
  min_speech_ms: 300
```

---

## 7. Dependencies

| Depends on | For what |
|---|---|
| **M6** | MinIO for audio blobs and TTS cache, Redis for pipeline-config cache, API gateway |
| **ontology/** | Lexicon files for masking (shared, but M2 is the main consumer) |

| Provides to | What |
|---|---|
| **M1** | TTS for the consent read-aloud and the language grid |
| **M3** | STT+translation inbound, translation+TTS outbound — the entire conversation |
| **M5** | TTS for the patient audio recap |
| **M4** | *Optional* — Bhashini printed-Indic OCR as one path (M4 decides whether to use it) |

---

## 8. Failure modes

| Failure | Required behaviour |
|---|---|
| Bhashini API down | Automatic switch to local models. Log it. Do not surface to the patient. |
| Bhashini API slow (> 4 s) | Timeout, fall through to local. Never let the patient wait 10 seconds. |
| Local models not loaded | Health endpoint reports it. Kiosk shows "please use touch input" and continues in touch-only mode. |
| ASR returns empty | Ask once more: "मैंने सुना नहीं, दोबारा बोलिए।" After 2 failures, offer touch input. |
| ASR confidence very low | Pass through with the low confidence attached. M3 decides whether to confirm. Do not silently drop. |
| NMT mangles a masked token | Detect unrestored tokens in the output. If any `⟦...⟧` survives, fall back to the unmasked source segment and log. |
| TTS fails | Show the text large on screen + a beep. Session continues. |
| Unsupported language requested | Return the supported list. Kiosk offers nearest available + English. |

---

## 9. Testing

**Unit**
- Masking: every lexicon entry masks and restores exactly
- Fuzzy masking: "met formin", "metformine", "मेटफॉर्मिन" all mask to the same token
- Unmask is lossless for a round trip
- Negation detection fires on Hindi/Tamil negation markers
- Code-mix normaliser handles the three sample sentences in §4.3

**Integration**
- Bhashini pipeline config caching — verify only one config call per language per TTL window
- Chained STT+NMT returns both texts in one call
- Force Bhashini offline → verify transparent local fallback, same response shape

**Performance**
- End-to-end turn latency p50 < 2.5 s, p95 < 3.5 s (cache warm)
- TTS cache hit rate > 70% after 20 simulated sessions

**Quality (this is the one that matters)**
- Build a small held-out set: **50 recorded utterances per primary language**, clinically realistic, recorded in noise
- Measure WER (word error rate) and, more importantly, **clinical-term accuracy** — did the drug names and durations survive?
- Report both. Clinical-term accuracy is the number to quote in the pitch.

---

## 10. Build order

**Phase 1 (vertical slice)**
- [ ] Bhashini account, API key, first successful STT call for Hindi
- [ ] `POST /lang/stt` and `POST /lang/tts` working end to end
- [ ] Audio blob stored in MinIO with offsets returned

**Phase 2 (depth)**
- [ ] Chained STT+NMT pipeline, config cached
- [ ] Protected-term masking with the drug + Ayurveda lexicons
- [ ] Code-mix normaliser
- [ ] Negation hint detection
- [ ] TTS cache
- [ ] VAD + noise suppression

**Phase 3 (differentiators)**
- [ ] Local model fallback, preloaded, transparent switching
- [ ] Speculative TTS pre-warming
- [ ] Health endpoint + latency metrics for the admin dashboard
- [ ] Language coverage extended to 10+ languages

---

## 11. Demo checklist — what M2 must show

1. **Patient speaks natural Hindi with code-mixing** — "मुझे 2 din se fever hai" — and it is understood correctly
2. **A drug name survives translation intact** — show the masked intermediate on the debug view if possible. This is a 10-second explanation that separates you from every other team.
3. **The question comes back in Hindi, spoken aloud** — full loop, under 3 seconds
4. **Pull the network cable.** The next question still works. Show the `engine: "local"` field flipping. This is USP #8.
5. **State the sovereignty line:** *"Patient audio is processed on Indian government infrastructure, or inside the hospital. It never goes to a foreign cloud."*

---

## 12. Notes and gotchas

- **Get the Bhashini API key on day 1.** Registration is not instant.
- **Cache the pipeline config.** This is the single biggest latency win and the easiest to miss.
- **Bhashini OCR is printed-text only.** It cannot read handwritten prescriptions. Do not promise M4 something you cannot deliver — hand them the printed path only, and let them own handwriting.
- **Do not send PII to Bhashini.** Audio only, with an opaque request token. No name, no ABHA ID, no session ID in the payload.
- **Test in actual noise.** Record your test set with a fan running and people talking. A model that works in a quiet room and fails in an OPD hall is not a working model.
- **Female voice by default for TTS** — user research in Indian health kiosks consistently shows higher comprehension and trust. Make it configurable, default it female.
- **Speak slower than default.** Elderly and low-literacy users need it. Reduce the TTS speech rate by ~10–15% and make it adjustable at the kiosk.

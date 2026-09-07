# M3 — Conversational History Engine

> **Owner:** Member 3
> **Read `00-INTRODUCTION.md` first.**
> **Service path:** `services/m3_conversation/`
> **Branch:** `m3-conversation`

---

## 1. Why this module exists

This is the module that replaces the part of the consultation that gets cut.

A doctor taking a history is not reading a form top to bottom. They are running an **adaptive search**: the answer to each question changes which question comes next. "Chest pain" opens a cardiac line of enquiry. "Loose motions" opens a GI one. That branching *is* the clinical skill.

M3 reproduces that branching structure — not the diagnostic reasoning, only the **elicitation** structure — so the history is complete before the patient sits down.

It also does something a paper form can never do: it watches for emergencies **while** it asks.

### The two hard requirements

1. **Adaptive, not a form.** The PS says explicitly: *"dynamically branches based on chief complaint and prior answers, mirroring a physician's clinical reasoning to elicit a complete HPI and review of systems."*
2. **Never diagnoses.** The PS says the summary must be *"never an autonomous diagnosis."* M3 asks questions and records answers. It does not conclude anything.

### The differentiator M3 owns

> **USP #3 — Live triage interrupt.** The red-flag detector runs *in parallel* with the interview, on every utterance. On a hit, the interview aborts mid-question, the kiosk alarms, and the patient's queue token is moved to the front. This converts the kiosk from a data-entry device into a triage instrument.

---

## 2. Responsibilities

| # | Responsibility | Detail |
|---|---|---|
| 1 | **Dialogue management** | Decide the next question given the current state |
| 2 | **Adaptive branching** | SOCRATES on the chief complaint, system-specific branches |
| 3 | **Review of Systems sweep** | Systematic symptom coverage |
| 4 | **AYUSH mode** | Dashavidha Pariksha + Ahara-Vihara branch for AYUSH OPDs |
| 5 | **Slot filling** | Convert free-text answers into typed, ontology-keyed slots |
| 6 | **Red-flag detection** | Parallel emergency screening on every utterance |
| 7 | **Dual-mode input** | Every question answerable by speaking **or** tapping |
| 8 | **Proxy handling** | Detect and tag answers given by a relative |
| 9 | **Session resume** | Patient wanders off → resume from last answered slot |
| 10 | **Completion policy** | Know when enough has been asked; never trap the patient |
| 11 | **Provenance emission** | Every slot carries the audio offset it came from |

### Explicitly NOT this module's job

- Speech recognition or translation (M2)
- Reading documents (M4)
- Writing the summary (M5)
- Deciding what disease the patient has (**nobody's job — we do not do this**)

---

## 3. Internal pipeline

```
        ENGLISH TEXT from M2          TOUCH EVENT from kiosk
        + audio provenance ref                 │
                    │                          │
                    └────────────┬─────────────┘
                                 ▼
                          TURN INTAKE
                    attach expected slot(s)
                    attach negation_hint
                    attach asr_confidence
                                 │
              ┌──────────────────┴──────────────────┐
              ▼                                     ▼
        SLOT FILLER                       ⚠ RED-FLAG ENGINE
        LLM constrained to                runs on EVERY utterance
        JSON grammar —                    in parallel, always
        cannot write prose                          │
              │                           ┌─────────┴─────────┐
              │                           ▼                   ▼
              ▼                    RULE ENGINE          ML CLASSIFIER
        emits per slot:            deterministic         recall net
          ontology_key             auditable            can RAISE a flag
          value                    PRIMARY              rules missed
          confidence                   │                can NEVER
          provenance                   │                suppress one
              │                        │                     │
              ▼                        └─────────┬───────────┘
        SLOT STORE                               ▼
                                          flag decision
              │                                  │
              │                        ┌─────────┴─────────┐
              │                        ▼                   ▼
              │                    POSITIVE            NEGATIVE
              │                        │                   │
              │                        ▼                   │
              │              ABORT INTERVIEW                │
              │              stop mid-question              │
              │              kiosk alarm + calm audio       │
              │              push to triage desk            │
              │              queue token → position 1       │
              │              notify physician on duty       │
              │              PARTIAL SLOTS PRESERVED        │
              │                                             │
              └─────────────────────┬───────────────────────┘
                                    ▼
                          DIALOGUE MANAGER
                    ontology-constrained state machine
                    state = filled slots + active branch
                            + section coverage
                                    │
                                    ▼
                            BRANCH SELECTOR
                                    │
        ┌───────────┬───────────┬───┴───┬───────────┬───────────┐
        ▼           ▼           ▼       ▼           ▼           ▼
   DEMOGRAPHICS  CHIEF     SOCRATES  SYSTEM     PAST HX      AYUSH
   age · sex   COMPLAINT   S·O·C·R·  BRANCH    medical      BRANCH
   from ABHA               A·T·E·S   cardiac   surgical    Prakriti
                                     resp      drugs       Vikriti
                                     GI        allergy     Agni
                                     neuro     family      Koshtha
                                     MSK       personal    Ahara-Vihara
                                     fever     ROS sweep   (if opd=ayush)
        │           │           │       │           │           │
        └───────────┴───────────┴───┬───┴───────────┴───────────┘
                                    │
                                    ▼
                        PROXY MODE (parallel tag)
                    relative answering → answered_by = proxy
                                    │
                                    ▼
                        NEXT-QUESTION POLICY
                    rank candidates by:
                      information gain
                      clinical priority
                      section coverage debt
                      time budget remaining
                                    │
                                    ▼
                          COMPLETION CHECK
                    done if mandatory slots filled
                       OR time budget exceeded
                       OR patient said stop
                       OR idle 90 s
                                    │
                    ┌───────────────┴───────────────┐
                    ▼                               ▼
                NOT DONE                          DONE
                    │                               │
                    ▼                               ▼
        English question text              hand off to M4 (documents)
        + tappable options                 then M5 (summary)
                    │
                    ▼
        → M2 (translate + speak)
                    │
                    └──────► loop
```

---

## 4. Component detail

### 4.1 The clinical ontology

Everything M3 does is driven by declarative YAML files in `ontology/`. **The dialogue logic is data, not code.** This is what lets a clinician-advisor review it, and what lets the team edit the interview without touching Python.

```
ontology/
├── socrates.yaml       # pain history framework
├── systems.yaml        # per-system question branches
├── ros.yaml            # review of systems sweep
├── dashavidha.yaml     # AYUSH ten-fold examination
├── prakriti.yaml       # constitution assessment instrument
├── red_flags.yaml      # emergency rules
└── general.yaml        # PMH, drugs, allergy, family, personal
```

**Question definition schema:**

```yaml
- id: hpi.pain.radiation
  section: hpi
  framework: socrates
  letter: R
  text_en: "Does the pain spread anywhere?"
  value_type: enum_multi
  options:
    - { key: left_arm,  label_en: "Left arm",  icon: "arm-left" }
    - { key: jaw,       label_en: "Jaw",       icon: "jaw" }
    - { key: back,      label_en: "Back",      icon: "back" }
    - { key: none,      label_en: "Nowhere",   icon: "none" }
  ask_if:
    - slot: hpi.complaint_type
      equals: pain
  priority: high
  mandatory: false
  contributes_to_red_flag: [CARDIAC-01, AORTIC-01]
```

**Key fields:**
- `ask_if` — the branching condition. This is the adaptive logic.
- `options` — every closed question **must** have icon-able options so a non-reader can tap
- `contributes_to_red_flag` — tells the red-flag engine this slot matters
- `mandatory` — drives the completion check
- `priority` — feeds the next-question ranking

### 4.2 SOCRATES branch

Fires when the chief complaint is pain-type. Eight sub-questions:

| Letter | Meaning | Slot key |
|---|---|---|
| **S** | Site — where is it | `hpi.pain.site` |
| **O** | Onset — when, sudden or gradual | `hpi.pain.onset`, `hpi.pain.onset_mode` |
| **C** | Character — burning, stabbing, dull, crushing | `hpi.pain.character` |
| **R** | Radiation — does it spread | `hpi.pain.radiation` |
| **A** | Associations — what comes with it | `hpi.pain.associations` |
| **T** | Time course — pattern over the day | `hpi.pain.time_course` |
| **E** | Exacerbating / relieving factors | `hpi.pain.exacerbating`, `hpi.pain.relieving` |
| **S** | Severity — 0 to 10 | `hpi.pain.severity` |

**Severity input design:** do not ask a low-literacy patient for a number. Use a **face scale** (6 faces, tappable) mapped to 0/2/4/6/8/10, with audio: "इनमें से कौन सा चेहरा आपके दर्द जैसा है?"

### 4.3 System-specific branches

After SOCRATES, the site determines which system branch runs.

```
site = chest   ──► cardiac branch + respiratory branch
site = abdomen ──► GI branch
site = head    ──► neuro branch
site = joints  ──► MSK branch
non-pain complaint ──► direct to the matching system branch
```

Each branch is a YAML file with its own `ask_if` conditions. **Start with 6 branches** (cardiac, respiratory, GI, neuro, MSK, general/fever) and add more if time allows. Six covers the overwhelming majority of OPD presentations.

### 4.4 AYUSH branch — Dashavidha Pariksha

Runs when `session.opd_type == "ayush"`. This is what makes the project AYUSH-native rather than a generic hospital app, and AIIA is the evaluating organisation. **Do not treat this as an afterthought.**

The ten-fold examination:

| # | Parameter | Meaning | How we elicit it |
|---|---|---|---|
| 1 | **Prakriti** | Body constitution (Vata/Pitta/Kapha) | Validated ~30-item questionnaire, scored |
| 2 | **Vikriti** | Current imbalance vs baseline | Derived from symptom pattern + direct questions |
| 3 | **Sara** | Tissue quality | Subset of observable/self-reportable items |
| 4 | **Samhanana** | Body build / compactness | Self-report + optionally staff-entered |
| 5 | **Pramana** | Body measurements | Height/weight from kiosk or staff |
| 6 | **Satmya** | What suits the patient (habituation) | Diet/climate/habit questions |
| 7 | **Sattva** | Mental strength | Short psychological resilience items |
| 8 | **Ahara Shakti** | Digestive/food capacity (Agni) | Appetite, digestion, bowel questions |
| 9 | **Vyayama Shakti** | Exercise capacity | Activity tolerance questions |
| 10 | **Vaya** | Age | From ABHA — no question needed |

Plus **Ahara-Vihara** (diet and lifestyle): meal timing, food type, sleep pattern, work pattern, physical activity.
Plus **Koshtha** (bowel nature): mridu / madhyama / krura.
Plus **Nidana** (causative factors) — asked as open "what do you think brought this on?"

**Prakriti scoring** lives in M5, but the *questions* live here. M3 fills the slots; M5 computes the dosha profile.

**Time management:** the full AYUSH branch is long. Budget it: if the interview has already run 6 minutes, ask only the high-priority Dashavidha items (Prakriti core, Agni, Koshtha, Ahara-Vihara) and mark the rest as not-assessed. **A partial AYUSH assessment is vastly better than none, which is what happens today.**

### 4.5 Red-flag engine (USP #3)

**Architecture: rules first, ML second, rules always win.**

```
utterance + current slot store
            │
    ┌───────┴────────┐
    ▼                ▼
RULE ENGINE      ML CLASSIFIER
deterministic    lightweight
auditable        recall net
    │                │
    │                │  can RAISE a flag the rules missed
    │                │  can NEVER suppress a rule-raised flag
    └───────┬────────┘
            ▼
      flag decision
```

**Why rules are primary:** a clinician must be able to read the rule that fired and agree with it. "The model said so" is not acceptable in a triage decision, and it is not defensible to a judge who is a doctor.

**Rule format:**

```yaml
- id: CARDIAC-01
  name: "Acute coronary syndrome pattern"
  severity: critical
  all_of:
    - slot: hpi.pain.site
      in: [chest, retrosternal, epigastric]
    - any_of:
        - { slot: hpi.pain.radiation, in: [left_arm, jaw, both_arms] }
        - { slot: hpi.pain.associations, contains: diaphoresis }
        - { slot: hpi.pain.associations, contains: dyspnoea }
    - slot: hpi.pain.onset
      within_hours: 24
  action: abort_and_escalate
  message_key: rf.cardiac.stop
  notify: [triage_desk, physician_on_duty]
```

**Minimum rule set to implement (12 rules covers the critical ground):**

| ID | Pattern |
|---|---|
| `CARDIAC-01` | Chest pain + radiation/diaphoresis/dyspnoea, recent onset |
| `STROKE-01` | FAST — face droop, arm weakness, speech difficulty, sudden onset |
| `RESP-01` | Severe breathlessness at rest, unable to complete a sentence |
| `BLEED-01` | Active significant bleeding, haematemesis, melaena |
| `SEPSIS-01` | Fever + confusion / very low urine output / rigors |
| `ABDO-01` | Sudden severe abdominal pain with rigidity |
| `NEURO-01` | Sudden worst-ever headache, or headache with neck stiffness + fever |
| `PEDS-01` | Infant < 3 months with fever |
| `OBS-01` | Pregnancy with bleeding or severe abdominal pain |
| `TRAUMA-01` | Recent head injury with vomiting or altered consciousness |
| `SUICIDE-01` | Expressed self-harm intent |
| `ANAPH-01` | Acute swelling of face/lips/tongue with breathing difficulty |

**The abort sequence — get this exactly right, it is the demo moment:**

```
1. Red-flag engine returns POSITIVE
2. Dialogue manager IMMEDIATELY stops. No further question is generated.
3. Kiosk plays a calm, clear audio message in the patient's language:
   "कृपया यहीं रुकें। नर्स अभी आ रही हैं।"
   ("Please stay here. A nurse is coming now.")
   — Calm, not alarming. Do not frighten the patient.
4. Screen goes to a high-contrast alert state with a single visual.
5. Alert(critical) emitted → M6 triage service
6. Triage board shows the patient, the rule that fired, and the timestamp
7. Queue token re-sequenced to position 1
8. Physician-on-duty notification
9. Partial slot store is preserved and handed to M5 —
   the doctor still gets whatever history was captured
```

**Rule 9 matters.** Aborting must not throw away what was collected. The doctor should walk in already knowing "chest pain, 3 days, radiates to left arm" even though the interview never finished.

### 4.6 Slot filler — the schema-locked LLM

**The safety mechanism is the grammar, not the prompt.**

The LLM is given a JSON schema for the *specific slot(s)* currently expected, and constrained decoding forces its output to conform. It literally cannot produce prose, cannot produce a diagnosis, cannot produce a drug recommendation — the grammar has no production rule for those.

```
Input to the model:
  question_asked:  "Does the pain spread anywhere?"
  patient_said:    "up to the left arm, and I've been sweating"
  expected_slots:  [hpi.pain.radiation, hpi.pain.associations]
  allowed_values:  { hpi.pain.radiation: [left_arm, jaw, back, none, other],
                     hpi.pain.associations: [diaphoresis, nausea, dyspnoea, ...] }

Grammar-constrained output (the ONLY shape it can emit):
  {
    "slots": [
      { "key": "hpi.pain.radiation",    "value": ["left_arm"],    "confidence": 0.94 },
      { "key": "hpi.pain.associations", "value": ["diaphoresis"], "confidence": 0.87 }
    ],
    "unrecognised": [],
    "needs_clarification": false
  }
```

**Implementation options:** llama.cpp GBNF grammars, vLLM guided decoding, or the Outlines library. All three enforce the schema at the decoding step, not by asking nicely in the prompt. Pick one and stay with it.

**Confidence handling:**
- `> 0.85` → accept
- `0.6 – 0.85` → accept but mark for confirmation in the recap
- `< 0.6` → ask a clarifying closed question ("क्या आपका मतलब बाएँ हाथ से है?")

### 4.7 Dual-mode input

Every question is answerable **both** ways, always. This is a PS requirement and an accessibility requirement.

| Question type | Voice | Touch |
|---|---|---|
| Closed enum | speak the option | tap an icon card |
| Yes/no | "हाँ" / "नहीं" | two large buttons |
| Severity | speak a number | 6-face pain scale |
| Duration | "तीन दिन से" | tappable: today / 2-3 days / a week / a month / longer |
| Site | describe it | tap a body diagram |
| Open text | speak freely | keyboard (rarely used, but present) |

**Body diagram for site selection** is worth building. It solves the case where a patient cannot name the anatomical location — very common, and it makes a strong demo visual.

### 4.8 Proxy mode

A relative frequently answers for an elderly patient. The doctor needs to know which answers are second-hand, because their reliability differs.

**Detection:**
- Explicit: a "someone is helping me" button on screen
- Implicit: speaker-change detection across turns (optional, if time permits)
- Linguistic: third-person references — "इनको दर्द है" ("*they* have pain") vs "मुझे दर्द है" ("*I* have pain")

**Effect:** slot is written with `answered_by: "proxy"`. M5 renders those lines with a marker. The doctor sees it.

### 4.9 Session resume

Patients wander off — to the toilet, to find a relative, because they got called. The session must survive it.

```
Session state is persisted after EVERY turn, not at the end.

Resume:
  patient re-scans ABHA at any kiosk
      │
      ▼
  active session found (within TTL)
      │
      ▼
  "आपने पहले जवाब देना शुरू किया था। वहीं से आगे बढ़ें?"
  [Continue]  [Start again]
      │
      ▼
  dialogue manager restores state, asks the next unanswered question
```

### 4.10 Completion policy — never trap the patient

```
Interview ends when ANY of:
  · all mandatory slots filled AND section coverage above threshold
  · time budget exceeded (default 8 minutes)
  · patient taps "I'm done" (always visible)
  · patient is silent/idle for 90 seconds after two prompts
  · red flag fired (abort path)

On any ending: whatever was captured goes to M5. A partial history
is still enormously more than the doctor has today.
```

**There is no mandatory question except consent.** Every clinical question can be skipped. A "Skip" affordance is always available.

---

## 5. API surface

```
POST   /api/v1/session/{id}/interview/start
       body  { opd_type, is_return_visit }
       →     { question, options, slot_keys, progress, estimated_remaining_s }

POST   /api/v1/session/{id}/turn
       body  { text_english, audio_provenance_ref, asr_confidence,
               negation_hint, touch_selection?, answered_by }
       →     { slots_filled: [...],
               next_question: { text_en, options, slot_keys, input_modes },
               progress: { section, percent, questions_asked },
               red_flag: null | { rule_id, severity, message_key },
               state: "continue" | "complete" | "aborted" }

POST   /api/v1/session/{id}/skip
       →     next question

POST   /api/v1/session/{id}/interview/end
       →     { slot_count, sections_covered, duration_s }

GET    /api/v1/session/{id}/slots
       →     [ Slot ]

GET    /api/v1/session/{id}/resume
       →     { resumable: bool, last_slot, next_question }

GET    /api/v1/ontology/questions?section=hpi&lang=en
       →     question definitions (for frontend pre-rendering)
```

---

## 6. Data model

```sql
CREATE TABLE slots (
    slot_id         UUID PRIMARY KEY,
    session_id      UUID NOT NULL,
    ontology_key    TEXT NOT NULL,
    value           JSONB NOT NULL,
    value_type      TEXT NOT NULL,
    unit            TEXT,
    confidence      REAL NOT NULL,
    framework       TEXT,            -- socrates | ros | dashavidha | general
    section         TEXT NOT NULL,
    answered_by     TEXT NOT NULL,   -- self | proxy
    input_mode      TEXT NOT NULL,   -- voice | touch
    provenance_id   UUID,
    superseded_by   UUID,            -- if patient corrected an answer
    created_at      TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX ON slots (session_id, ontology_key);

CREATE TABLE interview_state (
    session_id      UUID PRIMARY KEY,
    active_branch   TEXT,
    asked_keys      TEXT[],
    skipped_keys    TEXT[],
    section_coverage JSONB,
    started_at      TIMESTAMPTZ,
    last_turn_at    TIMESTAMPTZ,
    ended_at        TIMESTAMPTZ,
    end_reason      TEXT           -- complete | timeout | patient_stop | red_flag
);

CREATE TABLE red_flag_events (
    event_id        UUID PRIMARY KEY,
    session_id      UUID NOT NULL,
    rule_id         TEXT NOT NULL,
    severity        TEXT NOT NULL,
    triggering_slots UUID[],
    detector        TEXT NOT NULL,  -- rule | ml
    fired_at        TIMESTAMPTZ DEFAULT now(),
    acknowledged_by TEXT,
    acknowledged_at TIMESTAMPTZ
);
```

---

## 7. Dependencies

| Depends on | For what |
|---|---|
| **M1** | `session_id`, `opd_type`, patient age/sex from ABHA (drives some branches) |
| **M2** | Every inbound utterance (English text + provenance), every outbound question (translation + TTS) |
| **M6** | Database, API gateway, LLM runtime |
| **ontology/** | All question definitions and red-flag rules |

| Provides to | What |
|---|---|
| **M4** | Signal that the interview is done and document scanning may begin |
| **M5** | The slot store — the primary input to the summary |
| **M6** | Red-flag alerts for the triage service |

---

## 8. Failure modes

| Failure | Required behaviour |
|---|---|
| LLM slot filler returns invalid JSON | Grammar constraint should make this impossible. If it happens, retry once, then fall back to a keyword matcher, then ask the question as a closed tap-only question. |
| Patient gives an answer that fits no option | Store as `value: other, raw_text: "..."`. Never discard. M5 surfaces it verbatim to the doctor. |
| Patient is silent | Re-prompt once after 20 s, again after 40 s, then offer touch-only, then end gracefully at 90 s. |
| ASR confidence very low repeatedly | Switch that patient to touch-only mode for the rest of the session. Say so kindly. |
| Red-flag rule fires on a clearly false positive | Still escalate. **A false positive costs a nurse 30 seconds. A false negative costs a life.** Tune for recall, not precision. Log it for later rule tuning. |
| Interview exceeds time budget | End gracefully, hand partial slots to M5, tell the patient "बाकी डॉक्टर पूछ लेंगे." |
| Session resumed at a different kiosk | Works. State is server-side, keyed on ABHA. |

---

## 9. Testing

**Unit**
- Every `ask_if` condition evaluates correctly against a synthetic slot store
- Every red-flag rule fires on its positive fixture and does not fire on its negative fixture
- Slot filler grammar rejects any output containing prose or a disease name
- Completion policy terminates in all five end conditions

**Scenario tests (build these as fixtures — they are also your demo scripts)**

| Scenario | Expected behaviour |
|---|---|
| **S1 — Simple fever** | 12-question path, no red flag, completes in ~3 min |
| **S2 — Cardiac red flag** | Chest pain → SOCRATES → R answer triggers `CARDIAC-01` → abort at question 6, alert emitted, partial slots preserved |
| **S3 — AYUSH return visit** | Full Dashavidha branch runs, ~40 slots, Prakriti items all filled |
| **S4 — Proxy** | All slots tagged `answered_by: proxy` |
| **S5 — Abandonment + resume** | Session persists, resumes at correct question from a different kiosk |
| **S6 — Touch-only** | Complete interview with zero voice input |

**Clinical review**
- Get a doctor (any doctor — a friend, a family member, a professor) to read the SOCRATES and red-flag YAML and confirm the questions and rules are sensible. **This costs an hour and massively raises credibility in the pitch.**

---

## 10. Build order

**Phase 1 (vertical slice)**
- [ ] Ontology loader reading YAML
- [ ] Fixed 5-question linear interview (no branching)
- [ ] Slot filler with constrained decoding, writing to `slots` table
- [ ] `POST /turn` returns the next question

**Phase 2 (depth)**
- [ ] `ask_if` conditional branching engine
- [ ] Full SOCRATES branch
- [ ] 6 system branches
- [ ] ROS sweep
- [ ] AYUSH / Dashavidha branch + Prakriti instrument
- [ ] Next-question ranking policy
- [ ] Touch options for every question

**Phase 3 (differentiators)**
- [ ] Red-flag rule engine, 12 rules
- [ ] **Abort sequence with triage push and queue re-sequencing** ← the demo moment
- [ ] ML recall-net classifier
- [ ] Proxy detection
- [ ] Session resume
- [ ] Body-diagram site input

---

## 11. Demo checklist — what M3 must show

1. **The branch is visible.** After the patient says "chest pain", point at the screen: *"That radiation question only exists because they said chest pain. A form would have asked all 200 questions."*
2. **AYUSH branch running** — show the Agni/Koshtha questions, and say that today this assessment gets abbreviated out of existence.
3. **🚨 THE INTERRUPT.** Second scenario patient says chest pain radiating to the left arm with sweating. **The interview stops mid-question.** Alarm. Triage board updates live. Token 47 → 1. Say: *"This kiosk did not just save the doctor time. It found the one patient in the queue who could not wait."*
4. **Show the rule that fired** — `CARDIAC-01`, with its YAML. Deterministic, auditable, a clinician can read it. Contrast with "the model decided."
5. **Touch-only run** — do a complete interview without speaking, to prove accessibility.

---

## 12. Notes and gotchas

- **Ontology in YAML, not Python.** You will edit these files a hundred times. Make it data.
- **Tune red flags for recall.** Missing an MI to avoid annoying a nurse is the wrong trade. Say this out loud in the pitch — it shows clinical judgement.
- **Never let the LLM write prose.** The grammar constraint is not optional. It is the difference between a safe system and a liability.
- **Keep the interview under 8 minutes.** Beyond that, patients abandon and the queue backs up. Rank questions by information gain and cut the tail.
- **Do not ask what you already know.** Age and sex come from ABHA. Prior conditions come from the last encounter. Asking a returning diabetic "do you have diabetes?" destroys trust instantly.
- **Progress indicator is mandatory.** Patients need to see the end coming. Show dots and an estimated time.
- **Write the abort message copy carefully.** It must be calm and clear, not frightening. Get it translated properly, not machine-translated. A patient who panics at a kiosk is a bad outcome.
- **Preserve partial data on every exit path.** Abort, timeout, abandonment — the doctor gets whatever was collected.

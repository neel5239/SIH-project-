# SPEAK — voice assistant sub-module

**Module:** 02 — Patient Questionnaire
**Team:** all 6 members contribute · **Lead this sprint:** _assign in standup_
**Path:** `backend/02-questionnaire/speech_module`

---

## What this is for

**Sub-module A of two.** The patient answers by speaking, in their own language. This is the path most patients will use, and the one that makes the product usable by someone who cannot read.

## What it does

- Record the patient's answer and transcribe it
- Translate into English so the question engine has one language to reason in
- Speak every question aloud before it can be read
- Fall back to the type sub-module if speech keeps failing

## What you build here

| File | Does |
|---|---|
| `record.py` | capture, voice-activity detection, noise suppression |
| `stt.py` | speech to text — Bhashini / IndicConformer, provider-swappable |
| `translate.py` | local language ↔ English |
| `tts.py` | speak the question aloud, with a cache |
| `protect_terms.py` | never let the translator touch a drug name or a clinical term |
| `fallback.py` | switch this patient to typing after repeated failures |
| `audio_store.py` | store the recording + offsets so the doctor can replay it |

## Pipeline position

```
IN    microphone audio + the current question
OUT   the patient's answer as structured English + an audio reference
```

**Depends on:** a speech provider
**Feeds:** `question_engine/`

## Definition of done

- [ ] Every question is **spoken before it is read**
- [ ] Empty or unintelligible result → re-ask once, then offer typing. **Never a dead end.**
- [ ] Drug names and clinical terms survive translation intact
- [ ] **Test in real noise** — a hospital corridor, not a quiet room
- [ ] The audio reference lets the doctor replay exactly what the patient said

Default to a slower speech rate and a female voice — both measurably improve comprehension for elderly and low-literacy users. Start with **Hindi + English + one regional language, perfected.** Do not attempt twenty on day one.

## Reference

- `docs/PATIENT_FLOW.md — step 2`

---

*Shared folder. Any of the six can add files here — leave a line in this README when you do,
so the next person knows what exists.*

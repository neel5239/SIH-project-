# Handwritten Prescriptions  ★

**Module:** 03 — Document OCR
**Team:** all 6 members contribute · **Lead this sprint:** _assign in standup_
**Path:** `backend/03-document-ocr/handwritten_prescription`

---

## What this is for

The hardest thing in the project. A doctor's handwriting defeats ordinary OCR. Our position: **do not free-guess — constrain the vocabulary, and when confidence is low, refuse and ask a human.**

## What it does

- Detect which parts of the page are handwritten — most prescriptions are half printed
- Recognise the handwriting with a handwriting-specialised model
- Restrict the output to real Indian medicines so the model **cannot invent a drug**
- Read Indian prescription notation: `1-0-1`, `x5d`, `Tab.`, `SOS`, `BD`, `TDS`, `HS`

## What you build here

| File | Does |
|---|---|
| `detect.py` | printed vs handwritten regions |
| `recognise.py` | handwriting model — TrOCR class |
| `constrain.py` | restrict decoding to the real formulary |
| `formulary.txt` | Indian medicines — generics · brands · AYUSH formulations |
| `notation.py` | 1-0-1 → BD · x5d → 5 days · 1/2 → half tablet · ↑↓ |
| `extract.py` | medicine · strength · frequency · duration · route |

## Pipeline position

```
IN    a prescription page
OUT   structured medicines, each with a confidence score
```

**Depends on:** a handwriting model + the formulary list
**Feeds:** `extraction/` then module 04

## Definition of done

- [ ] **No output is ever a medicine that is not in the formulary list**
- [ ] Below the confidence floor: emit **no value**, keep the crop, and mark it for the doctor to confirm
- [ ] The doctor sees: *'Possible medicine: Metformin 500 mg · confidence 71% · ⚠ please verify'*
- [ ] **Do not claim perfect handwriting accuracy.** Say what the number is.

*Knowing that it cannot read a line is a stronger and safer result than a confident wrong drug name.* Say that sentence in the demo — a judge who understands medicine will recognise it immediately.

## Reference

- `docs/ARCHITECTURE.md — OCR`

---

*Shared folder. Any of the six can add files here — leave a line in this README when you do,
so the next person knows what exists.*

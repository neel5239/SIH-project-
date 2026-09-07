# Document Type Classifier

**Module:** 03 — Document OCR
**Team:** all 6 members contribute · **Lead this sprint:** _assign in standup_
**Path:** `backend/03-document-ocr/classifier`

---

## What this is for

A handwritten prescription, a lab report and an X-ray report each need a different pipeline. Routing wrongly wastes the whole downstream chain.

## What it does

- Identify the document type
- Route it to the correct extraction pipeline
- On low confidence, run more than one pipeline and merge

## What you build here

| File | Does |
|---|---|
| `classify.py` | the model |
| `router.py` | type → pipeline |
| `types.py` | prescription · lab_report · imaging_report · discharge · ecg · other |
| `train.py` | fine-tune on a few hundred labelled images |

## Pipeline position

```
IN    an uploaded page
OUT   document type + confidence
```

**Depends on:** a trained classifier
**Feeds:** the three extraction folders below

## Definition of done

- [ ] Six types distinguished
- [ ] Low confidence → run both plausible pipelines, keep the higher-confidence result
- [ ] An unrecognised document is still stored and shown to the doctor as an image

## Reference

- `docs/ARCHITECTURE.md`

---

*Shared folder. Any of the six can add files here — leave a line in this README when you do,
so the next person knows what exists.*

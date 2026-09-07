# Document Upload & Capture

**Module:** 03 — Document OCR
**Team:** all 6 members contribute · **Lead this sprint:** _assign in standup_
**Path:** `backend/03-document-ocr/upload`

---

## What this is for

Opens only when the patient said yes to reports or prescriptions. The patient uploads everything they brought — this is the moment a plastic bag of paper becomes data.

## What it does

- Accept photos from the kiosk camera or the patient's phone
- Accept PDFs and multi-page documents
- Check quality **before** accepting — blur, glare, cut-off corners — and guide a re-shoot
- Let the patient add as many documents as they have, one at a time

## What you build here

| File | Does |
|---|---|
| `upload.py` | accept images and PDFs, async job, returns immediately |
| `capture_qc.py` | blur · glare · corners · resolution, in under 150 ms |
| `hints.py` | spoken guidance: 'move it slightly left', 'more light needed' |
| `pdf_split.py` | multi-page PDF → pages |
| `store.py` | keep the ORIGINAL forever — every crop comes from it |

## Pipeline position

```
IN    images or PDFs from the patient
OUT   stored pages queued for processing
```

**Depends on:** object storage, an async queue
**Feeds:** `classifier/`

## Definition of done

- [ ] Upload returns **immediately**. OCR runs in the background; the patient never waits.
- [ ] Quality hints are **spoken**, not only shown
- [ ] After three failed attempts, **accept the document anyway** and send it for human verification. Never refuse the patient's paper.
- [ ] The original image is never overwritten

## Reference

- `docs/PATIENT_FLOW.md — step 4`

---

*Shared folder. Any of the six can add files here — leave a line in this README when you do,
so the next person knows what exists.*

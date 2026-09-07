# Imaging & Diagnostic Reports

**Module:** 03 — Document OCR
**Team:** all 6 members contribute · **Lead this sprint:** _assign in standup_
**Path:** `backend/03-document-ocr/imaging_reports`

---

## What this is for

Sonography, CT, MRI, X-ray, ECG. These are mostly **printed narrative reports** with an impression section — and that impression is what the doctor actually reads.

## What it does

- Recognise the modality: ultrasound · CT · MRI · X-ray · ECG · other
- Extract the study date, the body region and the **IMPRESSION / CONCLUSION** section
- Keep the full report text and the original image available
- **Never interpret the image itself.** We read the report; we do not diagnose from the scan.

## What you build here

| File | Does |
|---|---|
| `modality.py` | sonography · CT · MRI · X-ray · ECG · other |
| `sections.py` | findings · impression · advice |
| `impression.py` | pull out the impression — the line the doctor reads first |
| `ecg.py` | ECG reports: rate · rhythm · interval values from the printed strip header |
| `attach.py` | keep the full text and the original image linked to the visit |

## Pipeline position

```
IN    an imaging or ECG report page
OUT   modality · date · region · impression · full text · original image
```

**Depends on:** a printed-OCR engine
**Feeds:** module 04, doctor portal reports section

## Definition of done

- [ ] The **impression** is extracted and shown first — it is what the doctor reads
- [ ] The original image is always one tap away
- [ ] **We never analyse the scan itself.** No image-based diagnosis, ever. We read what the radiologist wrote.
- [ ] An unparseable report is still attached to the visit as an image with its date

Be explicit about this boundary in the pitch. Reading a radiologist's report is document understanding. Interpreting an X-ray is a different, regulated problem and we are not doing it.

## Reference

- `docs/ARCHITECTURE.md`

---

*Shared folder. Any of the six can add files here — leave a line in this README when you do,
so the next person knows what exists.*

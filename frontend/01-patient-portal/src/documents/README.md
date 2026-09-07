# Patient App — Documents

**Module:** Frontend — Patient App
**Team:** all 6 members contribute · **Lead this sprint:** _assign in standup_
**Path:** `frontend/01-patient-portal/src/documents`

---

## What this is for

Module 03 on the screen. Opens only if the patient said yes to reports or prescriptions.

## What it does

- Guided camera capture with live quality feedback
- Accept photos from the gallery and PDFs
- Let the patient add as many documents as they have
- Show what has been captured so far

## What you build here

| File | Does |
|---|---|
| `Upload.jsx` | the upload screen |
| `Camera.jsx` | ★ live overlay frame + spoken quality hints |
| `Gallery.jsx` | pick from the phone |
| `DocList.jsx` | what we have so far, with thumbnails |
| `Types.jsx` | prescription · lab report · sonography · CT · MRI · X-ray · ECG · other |
| `Done.jsx` | finish and send to the doctor |

## Pipeline position

```
IN    camera or gallery
OUT   uploaded documents
```

**Depends on:** `shared/api/documents`
**Feeds:** the patient

## Definition of done

- [ ] Quality hints are **spoken**, not only shown
- [ ] Upload never blocks — the patient can keep adding while earlier ones process
- [ ] After three failed attempts the document is **accepted anyway** and flagged for the doctor. Never refuse the patient's paper.
- [ ] 'I have nothing more' is always available

## Reference

- `docs/PATIENT_FLOW.md — step 4`

---

*Shared folder. Any of the six can add files here — leave a line in this README when you do,
so the next person knows what exists.*

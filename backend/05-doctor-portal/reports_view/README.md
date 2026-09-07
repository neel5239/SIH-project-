# Section 4 — Reports

**Module:** 05 — Doctor Portal
**Team:** all 6 members contribute · **Lead this sprint:** _assign in standup_
**Path:** `backend/05-doctor-portal/reports_view`

---

## What this is for

**At the bottom.** Everything the patient uploaded, digitised, dated and ordered — with the original image always one tap away.

## What it does

- List every uploaded document in chronological order
- Show the extracted content: medicines, lab values, imaging impressions
- Flag abnormal values and trends
- Show anything the system could not read, with the image, for the doctor to confirm

## What you build here

| File | Does |
|---|---|
| `documents.py` | the ordered document list |
| `medicines.py` | extracted prescriptions |
| `labs.py` | lab values + abnormal flags + trends |
| `imaging.py` | sonography · CT · MRI · X-ray · ECG impressions |
| `verify.py` | ⚠ items the system refused to guess — doctor confirms |
| `original.py` | serve the original image for any document |

## Pipeline position

```
IN    visit id
OUT   the reports block
```

**Depends on:** module 03
**Feeds:** doctor portal frontend

## Definition of done

- [ ] Chronological, deduplicated, with dates
- [ ] Abnormal lab values marked ↑ ↓ with the reference range shown
- [ ] A trend across dates is shown as a trend: *'HbA1c 9.2 → 8.6'*
- [ ] **Unreadable items are shown as unreadable, with the image**, never as a confident guess
- [ ] The original scan is always one tap away

## Reference

- `docs/DOCTOR_PORTAL.md — section 4`

---

*Shared folder. Any of the six can add files here — leave a line in this README when you do,
so the next person knows what exists.*

# Doctor Portal — The Four Sections

**Module:** Frontend — Doctor Portal
**Team:** all 6 members contribute · **Lead this sprint:** _assign in standup_
**Path:** `frontend/02-doctor-portal/src/sections`

---

## What this is for

The fixed vertical layout: **basic info → summary → questionnaire → reports.** This order is the product decision; do not change it.

## What it does

- Render each section as its own component
- Keep the summary directly above the questionnaire
- Make every source tag tappable
- Let the doctor edit in place

## What you build here

| File | Does |
|---|---|
| `BasicInfo.jsx` | ① name · age · sex · contact · chief complaint |
| `Summary.jsx` | ② ★★ the summary, every line with a source tag |
| `Questionnaire.jsx` | ③ the full Q&A the patient submitted |
| `Reports.jsx` | ④ documents, ordered, with abnormal flags |
| `EmergencyBanner.jsx` | 🚨 above everything, when it fired |
| `SourceTag.jsx` | ★★ [Patient] [Rx 12/04/25] [Lab 05/08/26] — tappable |
| `AudioReplay.jsx` | ★★ tap → hear the patient's own words |
| `ImageViewer.jsx` | ★★ tap → see the original document |
| `VerifyChip.jsx` | ⚠ unreadable · confidence 71% · confirm |
| `EditableLine.jsx` | doctor corrects a line |
| `ConfirmBar.jsx` | accept the record |

## Pipeline position

```
IN    the four blocks from module 05
OUT   the doctor's screen + corrections
```

**Depends on:** `shared/api/doctor`
**Feeds:** the physician

## Definition of done

- [ ] **Section order is fixed:** ① info ② summary ③ questionnaire ④ reports
- [ ] Every summary line has a tappable source tag
- [ ] Audio starts in **under 300 ms**
- [ ] A conflict shows as **two lines with two sources**, never merged
- [ ] Unreadable items show the image, never a confident guess
- [ ] Nothing is saved to the record until the doctor confirms

## Reference

- `docs/DOCTOR_PORTAL.md`

---

*Shared folder. Any of the six can add files here — leave a line in this README when you do,
so the next person knows what exists.*
